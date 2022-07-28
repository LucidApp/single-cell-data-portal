import gc
import logging
import time

import anndata
import numpy
import numpy as np
import scanpy
import tiledb
from scipy import sparse
from scipy.sparse import csr_matrix, coo_matrix

from backend.corpus_asset_pipelines.integrated_corpus.extract import get_X_raw
from backend.wmg.data.constants import (
    RANKIT_RAW_EXPR_COUNT_FILTERING_MIN_THRESHOLD,
    GENE_EXPRESSION_COUNT_MIN_THRESHOLD,
    INCLUDED_ASSAYS,
)
from backend.wmg.data.rankit import rankit
from backend.wmg.data.schemas.corpus_schema import INTEGRATED_ARRAY_NAME

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def apply_pre_concatenation_filters(
    anndata_object: anndata.AnnData, min_genes: int = GENE_EXPRESSION_COUNT_MIN_THRESHOLD
) -> anndata.AnnData:
    # Filter out cells with low coverage (less than GENE_EXPRESSION_COUNT_MIN_THRESHOLD unique genes expressed)
    scanpy.pp.filter_cells(anndata_object, min_genes=min_genes)

    # Filter out cells generated by assays that dont provide gene length normalization
    included_assay_ontology_ids = list(INCLUDED_ASSAYS.keys())
    anndata_object = anndata_object[
        anndata_object.obs["assay_ontology_term_id"].isin(included_assay_ontology_ids), :
    ].copy()
    return anndata_object


def transform_dataset_raw_counts_to_rankit(
    anndata_object: anndata.AnnData, corpus_path: str, global_var_index: numpy.ndarray, first_obs_idx: int
):
    """
    Apply rankit normalization to raw count expression values and save to the tiledb corpus object
    """
    array_name = f"{corpus_path}/{INTEGRATED_ARRAY_NAME}"
    expression_matrix = get_X_raw(anndata_object)
    stride = max(int(np.power(10, np.around(np.log10(1e9 / expression_matrix.shape[1])))), 10_000)
    with tiledb.open(array_name, mode="w") as array:
        for start in range(0, expression_matrix.shape[0], stride):
            end = min(start + stride, expression_matrix.shape[0])
            raw_expression_csr_matrix = sparse.csr_matrix(expression_matrix[start:end, :])

            # Compute RankIt
            rankit_integrated_csr_matrix = rankit(raw_expression_csr_matrix)

            rankit_integrated_coo_matrix = filter_out_rankits_with_low_expression_counts(
                rankit_integrated_csr_matrix, raw_expression_csr_matrix, expect_majority_filtered=True
            )

            global_rows = rankit_integrated_coo_matrix.row + start + first_obs_idx
            global_cols = global_var_index[rankit_integrated_coo_matrix.col]

            rankit_data = rankit_integrated_coo_matrix.data

            assert len(rankit_data) == len(global_rows)
            assert len(rankit_data) == len(global_cols)

            array[global_rows, global_cols] = {"rankit": rankit_data}
            del (
                raw_expression_csr_matrix,
                rankit_integrated_coo_matrix,
                rankit_integrated_csr_matrix,
                global_rows,
                global_cols,
                rankit_data,
            )
            gc.collect()

    logger.debug(f"Saved {array_name}.")


def filter_out_rankits_with_low_expression_counts(
    rankits: csr_matrix, raw_counts_csr: csr_matrix, expect_majority_filtered=True, verbose=False
) -> coo_matrix:
    """
    Keep only rankit values that were computed from expression values above the desired threshold.

    @param expect_majority_filtered: Set this to True if the caller expects the majority of rankit values will be
    filtered, as we can then use an optimal implementation
    """

    rankits_nnz_orig = rankits.nnz
    raw_counts = raw_counts_csr.tocoo(copy=False)
    to_keep_mask = raw_counts.data > RANKIT_RAW_EXPR_COUNT_FILTERING_MIN_THRESHOLD

    # Unfortunately, it seems to take longer to decide which strategy to use than it does to just run either one.
    # start = time.time()
    # expect_majority_filtered = to_keep_mask.sum() < rankits_nnz_orig / 2
    # end = time.time()
    # logger.info(f"filter_out_rankits_with_low_expression_counts(): use extract strategy={expect_majority_filtered}; "
    #             f"decision time={end - start}")

    start = time.time()

    if expect_majority_filtered:
        rows_to_keep = raw_counts.row[to_keep_mask]
        cols_to_keep = raw_counts.col[to_keep_mask]
        rankits_to_keep = rankits.data[to_keep_mask]
        rankits_filtered = coo_matrix((rankits_to_keep, (rows_to_keep, cols_to_keep)))
    else:
        to_filter_mask = ~to_keep_mask
        rows_to_filter = raw_counts.row[to_filter_mask]
        cols_to_filter = raw_counts.col[to_filter_mask]
        rankits[rows_to_filter, cols_to_filter] = 0.0
        rankits.eliminate_zeros()
        rankits_filtered = rankits.tocoo()

    end = time.time()
    if verbose is True:
        logger.info(
            f"filter duration={end - start}, "
            f"orig size={rankits_nnz_orig}, "
            f"abs reduction={rankits_nnz_orig - rankits_filtered.nnz}, "
            f"% reduction={(rankits_nnz_orig - rankits_filtered.nnz) / rankits_nnz_orig}"
        )

    return rankits_filtered
