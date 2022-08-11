/**
 * NOTE: If you modify this file, you must update Plausible custom event page for
 * both staging and prod environments as well.
 * Staging: https://plausible.io/cellxgene.staging.single-cell.czi.technology/settings/goals
 * Prod: https://plausible.io/cellxgene.cziscience.com/settings/goals
 */
export enum EVENTS {
  EXPLORE_CZ_CELLXGENE_ANNOTATE_CLICKED = "EXPLORE_CZ_CELLXGENE_ANNOTATE_CLICKED",
  FILTER_SELECT_ASSAY = "FILTER_SELECT_ASSAY",
  FILTER_SELECT_AUTHORS = "FILTER_SELECT_AUTHORS",
  FILTER_SELECT_CELL_COUNT = "FILTER_SELECT_CELL_COUNT",
  FILTER_SELECT_CELL_TYPE = "FILTER_SELECT_CELL_TYPE",
  FILTER_SELECT_DEVELOPMENT_STAGE = "FILTER_SELECT_DEVELOPMENT_STAGE",
  FILTER_SELECT_DISEASE = "FILTER_SELECT_DISEASE",
  FILTER_SELECT_ETHNICITY = "FILTER_SELECT_ETHNICITY",
  FILTER_SELECT_GENE_COUNT = "FILTER_SELECT_GENE_COUNT",
  FILTER_SELECT_ORGANISM = "FILTER_SELECT_ORGANISM",
  FILTER_SELECT_PUBLICATION_DATE = "FILTER_SELECT_PUBLICATION_DATE",
  FILTER_SELECT_SEX = "FILTER_SELECT_SEX",
  FILTER_SELECT_TISSUE = "FILTER_SELECT_TISSUE",
  WMG_SELECT_GENE = "WMG_SELECT_GENE",
  WMG_SELECT_ORGANISM = "WMG_SELECT_ORGANISM",
  WMG_SELECT_TISSUE = "WMG_SELECT_TISSUE",
  WMG_CLICK_NAV = "WMG_CLICK_NAV",
  WMG_HEATMAP_LOADED = "WMG_HEATMAP_LOADED",
  BROWSE_COLLECTIONS_CLICKED = "BROWSE_COLLECTIONS_CLICKED",
  WMG_CLICKED = "WMG_CLICKED",
  DATASET_EXPLORE_CLICKED = "DATASET_EXPLORE_CLICKED",
  BROWSE_TUTORIALS_CLICKED = "BROWSE_TUTORIALS_CLICKED",
  DATASETS_CLICK_NAV = "DATASETS_CLICK_NAV",
  COLLECTIONS_CLICK_NAV = "COLLECTIONS_CLICK_NAV",
  DOCUMENTATION_CLICK_NAV = "DOCUMENTATION_CLICK_NAV",
  HOMEPAGE_LEARN_FIND_SINGLE_CELL_DATA_CLICKED = "HOMEPAGE_LEARN_FIND_SINGLE_CELL_DATA_CLICKED",
  HOMEPAGE_LEARN_EXPLORE_GENE_EXPRESSION_CLICKED = "HOMEPAGE_LEARN_EXPLORE_GENE_EXPRESSION_CLICKED",
  HOMEPAGE_LEARN_ANALYZE_DATASETS_CLICKED = "HOMEPAGE_LEARN_ANALYZE_DATASETS_CLICKED",
  HOMEPAGE_LEARN_DOWNLOAD_DATA_CLICKED = "HOMEPAGE_LEARN_DOWNLOAD_DATA_CLICKED",
  HOMEPAGE_LEARN_EXPEDITE_COLLABORATION_CLICKED = "HOMEPAGE_LEARN_EXPEDITE_COLLABORATION_CLICKED",
  VIEW_COLLECTION_PAGE_CLICKED = "VIEW_COLLECTION_PAGE_CLICKED",
  DESKTOP_QUICK_START_DOC_CLICKED = "DESKTOP_QUICK_START_DOC_CLICKED",
  BROWSE_CAREERS_CLICKED = "BROWSE_CAREERS_CLICKED",
  GITHUB_CLICKED = "GITHUB_CLICKED",
  CONTACT_US_CLICKED = "CONTACT_US_CLICKED",
}
