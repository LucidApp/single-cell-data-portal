import { useContext, useMemo } from "react";
import { useQuery, UseQueryResult } from "react-query";
import { API_URL } from "src/configs/configs";
import { FMG_GENE_STRENGTH_THRESHOLD } from "src/views/WheresMyGene/common/constants";
import {
  DispatchContext,
  State,
  StateContext,
} from "src/views/WheresMyGene/common/store";
import { setSnapshotId } from "src/views/WheresMyGene/common/store/actions";
import {
  CellType,
  CellTypeGeneExpressionSummaryData,
  GeneExpressionSummary,
  RawCellTypeGeneExpressionSummaryData,
} from "src/views/WheresMyGene/common/types";
import { API } from "../API";
import { ROUTES } from "../constants/routes";
import { EMPTY_OBJECT } from "../constants/utils";
import { DEFAULT_FETCH_OPTIONS, JSON_BODY_FETCH_OPTIONS } from "./common";
import { ENTITIES } from "./entities";

interface RawOntologyTerm {
  [id: string]: string;
}

interface RawOntologyTermsByOrganism {
  [organismId: string]: Array<RawOntologyTerm>;
}
export interface RawPrimaryFilterDimensionsResponse {
  gene_terms: RawOntologyTermsByOrganism;
  organism_terms: Array<RawOntologyTerm>;
  snapshot_id: string;
  tissue_terms: RawOntologyTermsByOrganism;
}

export interface OntologyTerm {
  id: string;
  name: string;
}
interface OntologyTermsByOrganism {
  [organismID: string]: Array<OntologyTerm>;
}

export interface PrimaryFilterDimensionsResponse {
  genes: OntologyTermsByOrganism;
  organisms: Array<OntologyTerm>;
  snapshotId: string;
  tissues: OntologyTermsByOrganism;
}

export async function fetchPrimaryFilterDimensions(): Promise<PrimaryFilterDimensionsResponse> {
  const url = API_URL + API.WMG_PRIMARY_FILTER_DIMENSIONS;

  const response: RawPrimaryFilterDimensionsResponse = await (
    await fetch(url, DEFAULT_FETCH_OPTIONS)
  ).json();

  return transformPrimaryFilterDimensions(response);
}

function flattenOntologyTermsByOrganism(
  termsObject: RawOntologyTermsByOrganism
): OntologyTermsByOrganism {
  return Object.entries(termsObject).reduce((memo, [organismId, genes]) => {
    memo[organismId] = genes.map(toEntity);
    return memo;
  }, {} as OntologyTermsByOrganism);
}

export function generateTermsByKey(
  flattenedTerms: OntologyTermsByOrganism,
  key: keyof OntologyTerm
): {
  [key: string]: OntologyTerm;
} {
  const termsByKey: { [key: string]: OntologyTerm } = {};

  Object.values(flattenedTerms).forEach((terms) => {
    for (const term of terms) {
      termsByKey[term[key]] = term;
    }
  });

  return termsByKey;
}

function transformPrimaryFilterDimensions(
  response: RawPrimaryFilterDimensionsResponse
): PrimaryFilterDimensionsResponse {
  const { gene_terms, organism_terms, snapshot_id, tissue_terms } = response;

  return {
    genes: flattenOntologyTermsByOrganism(gene_terms),
    organisms: organism_terms.map(toEntity),
    snapshotId: snapshot_id,
    tissues: flattenOntologyTermsByOrganism(tissue_terms),
  };
}

export const USE_PRIMARY_FILTER_DIMENSIONS = {
  entities: [ENTITIES.WMG_PRIMARY_FILTER_DIMENSIONS],
  id: "wmg-primaryFilterDimensions",
};

export function usePrimaryFilterDimensions(): UseQueryResult<PrimaryFilterDimensionsResponse> {
  const dispatch = useContext(DispatchContext);

  // (thuang): Refresh query when the snapshotId changes
  const currentSnapshotId = useSnapshotId();

  return useQuery<PrimaryFilterDimensionsResponse>(
    [USE_PRIMARY_FILTER_DIMENSIONS, currentSnapshotId],
    fetchPrimaryFilterDimensions,
    {
      onSuccess(response) {
        if (!response || !dispatch) return;

        const { snapshotId } = response;

        if (currentSnapshotId !== snapshotId) {
          dispatch(setSnapshotId(snapshotId));
        }
      },
      // (thuang): We don't need to refetch during the session
      staleTime: Infinity,
    }
  );
}

interface Filter {
  gene_ontology_term_ids: string[];
  organism_ontology_term_id: string;
  tissue_ontology_term_ids: string[];
  dataset_ids: string[];
  disease_ontology_term_ids: string[];
  sex_ontology_term_ids: string[];
  development_stage_ontology_term_ids: string[];
  self_reported_ethnicity_ontology_term_ids: string[];
}

interface FilterSecondary {
  organism_ontology_term_id: string;
  tissue_ontology_term_ids: string[];
  dataset_ids: string[];
  disease_ontology_term_ids: string[];
  sex_ontology_term_ids: string[];
  development_stage_ontology_term_ids: string[];
  self_reported_ethnicity_ontology_term_ids: string[];
}

export interface FiltersQuery {
  filter: FilterSecondary;
}

export interface Query {
  filter: Filter;
}

interface QueryResponse {
  expression_summary: {
    // gene_ontology_term_id
    [geneId: string]: {
      [tissueId: string]: RawCellTypeGeneExpressionSummaryData[];
    };
  };
  snapshot_id: string;
  term_id_labels: {
    cell_types: {
      [tissue_type_ontology_term_id: string]: {
        cell_type: string;
        cell_type_ontology_term_id: string;
        depth: number;
        total_count: number;
      }[];
    };
    genes: {
      [id: string]: string;
    }[];
  };
}

interface FiltersQueryResponse {
  filter_dims: {
    datasets: {
      collection_id: string;
      collection_label: string;
      id: string;
      label: string;
    }[];
    disease_terms: { [id: string]: string }[];
    sex_terms: { [id: string]: string }[];
    development_stage_terms: { [id: string]: string }[];
    self_reported_ethnicity_terms: { [id: string]: string }[];
    tissue_terms: { [id: string]: string }[];
  };
  snapshot_id: string;
}

async function fetchFiltersQuery({
  query,
  signal,
}: {
  query: FiltersQuery | null;
  signal?: AbortSignal;
}): Promise<FiltersQueryResponse | undefined> {
  if (!query) return;

  const url = API_URL + API.WMG_FILTERS_QUERY;

  const response = await fetch(url, {
    ...DEFAULT_FETCH_OPTIONS,
    ...JSON_BODY_FETCH_OPTIONS,
    body: JSON.stringify(query),
    method: "POST",
    signal,
  });
  const json: FiltersQueryResponse = await response.json();

  if (!response.ok) {
    throw json;
  }

  return json;
}

async function fetchQuery({
  query,
  signal,
}: {
  query: Query | null;
  signal?: AbortSignal;
}): Promise<QueryResponse | undefined> {
  if (!query) return;

  const url = API_URL + API.WMG_QUERY;

  const response = await fetch(url, {
    ...DEFAULT_FETCH_OPTIONS,
    ...JSON_BODY_FETCH_OPTIONS,
    body: JSON.stringify(query),
    method: "POST",
    signal,
  });
  const json: QueryResponse = await response.json();

  if (!response.ok) {
    throw json;
  }

  return json;
}

export const USE_QUERY = {
  entities: [ENTITIES.WMG_QUERY],
  id: "wmg-query",
};

export const USE_FILTERS_QUERY = {
  entities: [ENTITIES.WMG_FILTERS_QUERY],
  id: "wmg-filters-query",
};

export function useWMGQuery(
  query: Query | null
): UseQueryResult<QueryResponse> {
  const dispatch = useContext(DispatchContext);

  // (thuang): Refresh query when the snapshotId changes
  const currentSnapshotId = useSnapshotId();

  query = clobberQueryIfSubsetOfPrev(query, [
    "gene_ontology_term_ids",
    "tissue_ontology_term_ids",
  ]);

  return useQuery(
    [USE_QUERY, query, currentSnapshotId],
    ({ signal }) => fetchQuery({ query, signal }),
    {
      enabled: Boolean(query),
      onSuccess(response) {
        if (!response || !dispatch) return;

        const { snapshot_id } = response;

        if (currentSnapshotId !== snapshot_id) {
          dispatch(setSnapshotId(snapshot_id));
        }
      },
      // (thuang): We don't need to refetch during the session
      staleTime: Infinity,
    }
  );
}

export function useWMGFiltersQuery(
  query: FiltersQuery | null
): UseQueryResult<FiltersQueryResponse> {
  const dispatch = useContext(DispatchContext);

  // (thuang): Refresh query when the snapshotId changes
  const currentSnapshotId = useSnapshotId();

  return useQuery(
    [USE_FILTERS_QUERY, query, currentSnapshotId],
    ({ signal }) => fetchFiltersQuery({ query, signal }),
    {
      enabled: Boolean(query),
      onSuccess(response) {
        if (!response || !dispatch) return;

        const { snapshot_id } = response;

        if (currentSnapshotId !== snapshot_id) {
          dispatch(setSnapshotId(snapshot_id));
        }
      },
      // (thuang): We don't need to refetch during the session
      staleTime: Infinity,
    }
  );
}

const EMPTY_FILTER_DIMENSIONS = {
  datasets: [],
  development_stage_terms: [],
  disease_terms: [],
  self_reported_ethnicity_terms: [],
  sex_terms: [],
  tissue_terms: [],
};

export interface RawDataset {
  collection_id: string;
  collection_label: string;
  id: string;
  label: string;
}

export interface FilterDimensions {
  datasets: RawDataset[];
  development_stage_terms: { id: string; name: string }[];
  disease_terms: { id: string; name: string }[];
  self_reported_ethnicity_terms: { id: string; name: string }[];
  sex_terms: { id: string; name: string }[];
  tissue_terms: { id: string; name: string }[];
}

export function useFilterDimensions(): {
  data: FilterDimensions;
  isLoading: boolean;
} {
  const requestBody = useWMGFiltersQueryRequestBody();
  const { data, isLoading } = useWMGFiltersQuery(requestBody);

  return useMemo(() => {
    if (isLoading || !data) return { data: EMPTY_FILTER_DIMENSIONS, isLoading };

    const { filter_dims } = data;

    const {
      datasets,
      development_stage_terms,
      disease_terms,
      self_reported_ethnicity_terms,
      sex_terms,
      tissue_terms,
    } = filter_dims;

    const sortedDatasets = Object.values(
      aggregateCollectionsFromDatasets(datasets)
    ).flatMap(({ datasets }) => datasets);

    return {
      data: {
        datasets: sortedDatasets.map((dataset) => ({
          ...dataset,
          name: dataset.label,
        })),
        development_stage_terms: development_stage_terms.map(toEntity),
        disease_terms: disease_terms.map(toEntity),
        self_reported_ethnicity_terms:
          self_reported_ethnicity_terms.map(toEntity),
        sex_terms: sex_terms.map(toEntity),
        tissue_terms: tissue_terms.map(toEntity),
      },
      isLoading: false,
    };
  }, [data, isLoading]);
}

export function useExpressionSummary(): {
  isLoading: boolean;
  data: QueryResponse["expression_summary"];
} {
  const requestBody = useWMGQueryRequestBody();

  const { data, isLoading } = useWMGQuery(requestBody);

  return useMemo(() => {
    if (isLoading || !data) return { data: EMPTY_OBJECT, isLoading };

    const { expression_summary } = data;

    return {
      data: expression_summary,
      isLoading: false,
    };
  }, [data, isLoading]);
}

export interface CellTypeByTissueName {
  [tissueName: string]: CellType[];
}

export function useCellTypesByTissueName(): {
  isLoading: boolean;
  data: CellTypeByTissueName;
} {
  const { data, isLoading } = useExpressionSummary();
  const {
    data: primaryFilterDimensions,
    isLoading: isLoadingPrimaryFilterDimensions,
  } = usePrimaryFilterDimensions();

  const { data: termIdLabels, isLoading: isLoadingTermIdLabels } =
    useTermIdLabels();
  return useMemo(() => {
    if (
      isLoading ||
      isLoadingPrimaryFilterDimensions ||
      !primaryFilterDimensions ||
      isLoadingTermIdLabels ||
      !Object.keys(termIdLabels.cell_types).length
    ) {
      return { data: EMPTY_OBJECT, isLoading };
    }
    const { tissues } = primaryFilterDimensions;

    const tissuesById = generateTermsByKey(tissues, "id");

    const cellTypesByTissueName: { [tissueName: string]: CellType[] } = {};

    for (const [tissueId, rawTissueCellTypes] of Object.entries(
      termIdLabels.cell_types
    )) {
      const tissueName = tissuesById[tissueId].name;

      const tissueCellTypes = Object.entries(rawTissueCellTypes)
        // (thuang): Reverse the order, so the first cell type is at the top of
        // the heat map
        .reverse()
        .map(([cellTypeId, cellTypeName]) => {
          return {
            id: cellTypeId,
            ...cellTypeName,
          };
        });

      cellTypesByTissueName[tissueName] = tissueCellTypes;
    }

    return {
      data: cellTypesByTissueName,
      isLoading,
    };
  }, [
    data,
    isLoading,
    primaryFilterDimensions,
    isLoadingPrimaryFilterDimensions,
    termIdLabels,
    isLoadingTermIdLabels,
  ]);
}

export interface GeneExpressionSummariesByTissueName {
  [tissueName: string]: { [geneName: string]: GeneExpressionSummary };
}

export function useGeneExpressionSummariesByTissueName(): {
  data: GeneExpressionSummariesByTissueName;
  isLoading: boolean;
} {
  const { data, isLoading } = useExpressionSummary();

  const {
    data: primaryFilterDimensions,
    isLoading: isLoadingPrimaryFilterDimensions,
  } = usePrimaryFilterDimensions();

  const { data: termIdLabels, isLoading: isLoadingTermIdLabels } =
    useTermIdLabels();

  return useMemo(() => {
    if (
      isLoading ||
      !data ||
      isLoadingPrimaryFilterDimensions ||
      !primaryFilterDimensions ||
      isLoadingTermIdLabels ||
      !termIdLabels
    ) {
      return { data: EMPTY_OBJECT, isLoading };
    }

    const { tissues } = primaryFilterDimensions;

    const tissuesById = generateTermsByKey(tissues, "id");

    const result: {
      [tissueName: string]: { [geneName: string]: GeneExpressionSummary };
    } = {};

    for (const [geneId, expressionSummariesByTissue] of Object.entries(data)) {
      const geneName = termIdLabels.genes[geneId];

      for (const [tissueId, expressionSummaries] of Object.entries(
        expressionSummariesByTissue
      )) {
        const tissueName = tissuesById[tissueId].name;

        const tissueGeneExpressionSummaries: {
          [geneName: string]: GeneExpressionSummary;
        } = result[tissueName] || {};

        tissueGeneExpressionSummaries[geneName] = {
          cellTypeGeneExpressionSummaries: expressionSummaries.map(
            transformCellTypeGeneExpressionSummaryData
          ),
          name: geneName,
        };

        result[tissueName] = tissueGeneExpressionSummaries;
      }
    }

    return { data: result, isLoading };
  }, [
    data,
    isLoading,
    primaryFilterDimensions,
    isLoadingPrimaryFilterDimensions,
    termIdLabels,
    isLoadingTermIdLabels,
  ]);
}

function transformCellTypeGeneExpressionSummaryData(
  data: RawCellTypeGeneExpressionSummaryData
): CellTypeGeneExpressionSummaryData {
  const { id, pc, me, tpc, n } = data;

  return {
    ...data,
    expressedCellCount: n,
    id,
    meanExpression: me,
    percentage: pc,
    tissuePercentage: tpc,
  };
}

interface TermIdLabels {
  cell_types: {
    [tissueID: string]: {
      [id: string]: { name: string; depth: number; total_count: number };
    };
  };
  genes: { [id: string]: string };
}

export function useTermIdLabels(): {
  data: TermIdLabels;
  isLoading: boolean;
} {
  const requestBody = useWMGQueryRequestBody();
  const { data, isLoading } = useWMGQuery(requestBody);
  return useMemo(() => {
    if (isLoading || !data) {
      return {
        data: { cell_types: EMPTY_OBJECT, genes: EMPTY_OBJECT },
        isLoading,
      };
    }
    const {
      term_id_labels: { cell_types, genes },
    } = data;
    const returnCellTypes: TermIdLabels["cell_types"] = {};
    Object.entries(cell_types).forEach(([tissueID, cell_types]) => {
      const result: {
        [id: string]: { name: string; depth: number; total_count: number };
      } = {};
      for (const {
        cell_type_ontology_term_id,
        cell_type,
        depth,
        total_count,
      } of cell_types) {
        result[cell_type_ontology_term_id] = {
          depth,
          name: cell_type,
          total_count,
        };
      }
      returnCellTypes[tissueID] = result;
    });
    return {
      data: {
        cell_types: returnCellTypes,
        genes: aggregateIdLabels(genes),
      },
      isLoading: false,
    };
  }, [data, isLoading]);
}

function aggregateIdLabels(items: { [id: string]: string }[]): {
  [id: string]: string;
} {
  return items.reduce((memo, item) => ({ ...memo, ...item }), {});
}

function useWMGQueryRequestBody() {
  const {
    selectedGenes,
    selectedTissues,
    selectedOrganismId,
    selectedFilters,
  } = useContext(StateContext);
  const { data } = usePrimaryFilterDimensions();

  const { datasets, developmentStages, diseases, ethnicities, sexes } =
    selectedFilters;
  const organismGenesByName = useMemo(() => {
    const result: { [name: string]: { id: string; name: string } } = {};

    if (!data || !selectedOrganismId) return result;

    const { genes } = data;

    const organismGenes = genes[selectedOrganismId];

    for (const gene of organismGenes) {
      result[gene.name] = gene;
    }

    return result;
  }, [data, selectedOrganismId]);

  // seve: This is a nice mapping that may start being used in a few places across WMG, might be worth moving to a global store.
  const tissuesByName = useMemo(() => {
    let result: { [name: string]: OntologyTerm } = {};

    if (!data) return result;

    const { tissues } = data;

    result = generateTermsByKey(tissues, "name");

    return result;
  }, [data]);

  return useMemo(() => {
    if (!data || !selectedOrganismId || !selectedTissues.length) {
      return null;
    }
    const gene_ontology_term_ids = selectedGenes.map((geneName) => {
      return organismGenesByName[geneName].id;
    });
    if (!gene_ontology_term_ids.length) gene_ontology_term_ids.push(".");
    const tissue_ontology_term_ids = selectedTissues.map((tissueName) => {
      return tissuesByName[tissueName].id;
    });

    return {
      filter: {
        dataset_ids: datasets,
        development_stage_ontology_term_ids: developmentStages,
        disease_ontology_term_ids: diseases,
        gene_ontology_term_ids,
        organism_ontology_term_id: selectedOrganismId,
        self_reported_ethnicity_ontology_term_ids: ethnicities,
        sex_ontology_term_ids: sexes,
        tissue_ontology_term_ids,
      },
      is_rollup: true, // this could be made toggleable by users in the future
    };
  }, [
    selectedGenes,
    selectedTissues,
    selectedOrganismId,
    data,
    organismGenesByName,
    tissuesByName,
    datasets,
    developmentStages,
    diseases,
    ethnicities,
    sexes,
  ]);
}

function useWMGFiltersQueryRequestBody() {
  const { selectedTissues, selectedOrganismId, selectedFilters } =
    useContext(StateContext);
  const { data } = usePrimaryFilterDimensions();

  const { datasets, developmentStages, diseases, ethnicities, sexes } =
    selectedFilters;

  const tissuesByName = useMemo(() => {
    let result: { [name: string]: OntologyTerm } = {};

    if (!data) return result;

    const { tissues } = data;

    result = generateTermsByKey(tissues, "name");

    return result;
  }, [data]);

  return useMemo(() => {
    if (!data || !selectedOrganismId) {
      return null;
    }
    const tissue_ontology_term_ids = selectedTissues.map((tissueName) => {
      return tissuesByName[tissueName].id;
    });

    return {
      filter: {
        dataset_ids: datasets,
        development_stage_ontology_term_ids: developmentStages,
        disease_ontology_term_ids: diseases,
        organism_ontology_term_id: selectedOrganismId,
        self_reported_ethnicity_ontology_term_ids: ethnicities,
        sex_ontology_term_ids: sexes,
        tissue_ontology_term_ids,
      },
    };
  }, [
    selectedTissues,
    selectedOrganismId,
    data,
    tissuesByName,
    datasets,
    developmentStages,
    diseases,
    ethnicities,
    sexes,
  ]);
}

let prevQuery: Query | null;

function clobberQueryIfSubsetOfPrev(
  query: Query | null,
  filtersToCheck: (keyof Filter)[]
): Query | null {
  if (prevQuery == query) return prevQuery;
  if (!prevQuery || !query) {
    prevQuery = query;
    return query;
  }
  if (
    (Object.entries(query.filter) as [keyof Filter, string[]][]).every(
      ([key, value]) => {
        //just check for equality on the filters we aren't checking for subsets
        if (!filtersToCheck.includes(key))
          return (
            JSON.stringify(value) === JSON.stringify(prevQuery?.filter[key])
          );
        return value.every((elem) => prevQuery?.filter[key].includes(elem));
      }
    )
  ) {
    return prevQuery;
  }
  prevQuery = query;
  return query;
}

function toEntity(item: RawOntologyTerm) {
  const [id, name] = Object.entries(item)[0];

  return { id, name: name || id || "" };
}

function useSnapshotId(): string | null {
  const state = useContext(StateContext);

  const { snapshotId } = state;

  return snapshotId || null;
}

interface Dataset extends RawDataset {
  id: string;
  label: string;
}

export const EMPTY_FILTERS: State["selectedFilters"] = {
  datasets: [],
  developmentStages: [],
  diseases: [],
  ethnicities: [],
  sexes: [],
};
export interface CollectionFromDatasets {
  name: string;
  url: string;
  datasets: Dataset[];
}

export interface CollectionsFromDatasets {
  [name: string]: CollectionFromDatasets;
}

export function aggregateCollectionsFromDatasets(
  datasets: FilterDimensions["datasets"]
): CollectionsFromDatasets {
  const collections: CollectionsFromDatasets = {};

  for (const dataset of datasets) {
    const { collection_label, collection_id, id, label } = dataset;

    if (!collections[collection_label]) {
      collections[collection_label] = {
        datasets: [],
        name: collection_label,
        url: ROUTES.COLLECTION.replace(":id", collection_id),
      };
    }

    collections[collection_label].datasets.push({ ...dataset, id, label });
  }

  for (const collection of Object.values(collections)) {
    collection.datasets.sort((a, b) => {
      return a.label.localeCompare(b.label);
    });
  }

  return collections;
}

interface MarkerGeneRequestBody {
  celltype: string;
  n_markers: number;
  organism: string;
  test: "ttest" | "binomtest";
  tissue: string;
}

interface HardcodedMarkerGeneRequest extends MarkerGeneRequestBody {
  n_markers: 25;
}

export function generateMarkerGeneBody(
  cellTypeID: string,
  tissueID: string,
  organismID: string,
  test: "ttest" | "binomtest"
): HardcodedMarkerGeneRequest {
  return {
    celltype: cellTypeID,
    n_markers: 25,
    organism: organismID,
    test: test,
    tissue: tissueID,
  };
}

export interface FetchMarkerGeneParams {
  cellTypeID: string;
  tissueID: string;
  organismID: string;
  test?: "ttest" | "binomtest";
}

export async function fetchMarkerGenes({
  cellTypeID,
  organismID,
  tissueID,
  test = "ttest",
}: FetchMarkerGeneParams): Promise<MarkerGeneResponse> {
  const url = API_URL + API.WMG_MARKER_GENES;
  const body = generateMarkerGeneBody(cellTypeID, tissueID, organismID, test);
  const response = await fetch(url, {
    ...DEFAULT_FETCH_OPTIONS,
    ...JSON_BODY_FETCH_OPTIONS,
    body: JSON.stringify(body),
    method: "POST",
  });

  const json: MarkerGeneResponse = await response.json();

  if (!response.ok) {
    throw json;
  }

  return json;
}
export const USE_MARKER_GENES = {
  ENTITIES: [ENTITIES.WMG_MARKER_GENES],
  id: "wmg-marker-genes",
};

export interface MarkerGenesByCellType {
  [cellType: string]: MarkerGeneResponse["marker_genes"];
}

export interface MarkerGene {
  gene_ontology_term_id: string;
  effect_size: number;
  p_value: number;
}

export interface MarkerGeneResponse<T = MarkerGene[]> {
  marker_genes: T;
  snapshot_id: string;
}

export function useMarkerGenes({
  cellTypeID,
  organismID,
  tissueID,
  test,
}: FetchMarkerGeneParams): UseQueryResult<MarkerGeneResponse<MarkerGene>> {
  const { data } = usePrimaryFilterDimensions();
  const genesByID = useMemo((): { [name: string]: OntologyTerm } => {
    let result: { [name: string]: OntologyTerm } = {};

    if (!data) return result;

    const { genes } = data;

    result = generateTermsByKey(genes, "id");

    return result;
  }, [data]);

  function filterMarkerGenes(markerGenes: MarkerGene[]): MarkerGene[] {
    return markerGenes.filter(
      (markerGene) => markerGene.effect_size >= FMG_GENE_STRENGTH_THRESHOLD
    );
  }

  return useQuery(
    /**
     * (thuang): Add all arguments to `fetchMarkerGenes()` as dependencies,
     * so React Query can cache responses correctly without running into
     * issues like #4161
     */
    [USE_MARKER_GENES, cellTypeID, organismID, test, tissueID],
    async () => {
      const output = await fetchMarkerGenes({
        cellTypeID,
        organismID,
        test,
        tissueID,
      });
      const markerGenesIndexedByGeneName = Object.fromEntries(
        filterMarkerGenes(output.marker_genes).reduce(
          (newEntries, { gene_ontology_term_id, ...data }) => {
            try {
              newEntries.push([genesByID[gene_ontology_term_id].name, data]);
            } catch (e) {
              console.log("could not find gene with id", gene_ontology_term_id);
            }
            return newEntries;
          },
          [] as [string, Partial<MarkerGene>][]
        )
      );
      return { ...output, marker_genes: markerGenesIndexedByGeneName };
    },
    {
      staleTime: Infinity,
    }
  );
}
