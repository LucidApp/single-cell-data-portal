import { EMPTY_ARRAY } from "src/common/constants/utils";
import {
  getOntologyTermIdFromCellTypeViewId,
  getOptionIdFromCellTypeViewId,
  OptionId,
} from "src/common/queries/wheresMyGene";
import {
  CellType,
  CellTypeSummary,
  GeneExpressionSummary,
  Tissue,
} from "../../common/types";
import { TISSUE_CELL_TYPE_DIVIDER } from "./hooks/useSortedGeneNames";

export const Y_AXIS_CHART_WIDTH_PX = 352;

/**
 * Used to calculate text pixel widths. Should be only created once.
 */
const CTX =
  (typeof document !== "undefined" &&
    document.createElement("canvas").getContext("2d")) ||
  null;

/**
 * Formats and truncates the cell type name to a given width
 *
 * @param name The text to truncate
 * @param maxWidth The max width in pixels the string should be
 * @param font The font family and font size as a string. Ex. "bold 12px sans-serif"
 * @returns The string fixed to a certain pixel width
 */
export function formatLabel(
  name: string,
  maxWidth: number,
  font: string
): {
  text: string;
  length: number;
} {
  // failsafe, should never be falsy
  if (!CTX) return { text: name, length: 0 };

  CTX.font = font;
  const ellipsisWidth = CTX.measureText("...").width;

  const fullWidth = CTX.measureText(name).width;

  if (fullWidth <= maxWidth) {
    return {
      text: name,
      length: fullWidth,
    };
  }

  const labelHalfWidth = (maxWidth - ellipsisWidth) / 2;

  const firstHalf = getFixedWidth(name, labelHalfWidth, font);
  const secondHalf = getFixedWidth(name, labelHalfWidth, font, true);

  const formattedLabel = firstHalf + "..." + secondHalf;

  return {
    text: formattedLabel,
    length: CTX.measureText(formattedLabel).width,
  };
}

/**
 * Truncates the string to a given width
 *
 * @param text The text to truncate
 * @param maxWidth The max width in pixels the string should be
 * @param font The font family and font size as a string. Ex. "bold 12px sans-serif"
 * @param reverse Whether to truncate the end or beginning of the string
 * @returns The string fixed to a certain pixel width
 */
export function getFixedWidth(
  text: string,
  maxWidth: number,
  font: string,
  reverse = false
): string {
  // failsafe, should never be falsy
  if (!CTX) return text;

  CTX.font = font;

  if (reverse) {
    for (let i = text.length; i >= 0; i--) {
      const substring = text.substring(i - 1);
      const textWidth = CTX.measureText(substring).width;
      if (textWidth > maxWidth) {
        return text.substring(i);
      }
    }
  } else {
    for (let i = 0; i < text.length; i++) {
      const substring = text.substring(0, i + 1);
      const textWidth = CTX.measureText(substring).width;
      if (textWidth > maxWidth) {
        return text.substring(0, i);
      }
    }
  }

  return text;
}

export const HEAT_MAP_BASE_HEIGHT_PX = 300;
export const HEAT_MAP_BASE_CELL_PX = 20;
export const HEAT_MAP_BASE_CELL_WIDTH_PX = 20;

/**
 * Approximating the heatmap width by the number of genes.
 * This is used to make sure the table cell size stays the same regardless
 * of the number of genes selected.
 */
export function getHeatmapWidth(
  genes: (GeneExpressionSummary | undefined)[] | string[] = EMPTY_ARRAY
): number {
  return HEAT_MAP_BASE_CELL_WIDTH_PX * genes.length;
}

/**
 * Approximating the heatmap height by the number of cells.
 */
export function getHeatmapHeight(cellTypes: CellType[] = EMPTY_ARRAY): number {
  return HEAT_MAP_BASE_CELL_PX * cellTypes.length;
}

/**
 * Value format: `${viewId}~${tissue}~${name}~${order}`
 */
export type CellTypeMetadata =
  `${CellTypeSummary["viewId"]}~${Tissue}~${CellTypeSummary["name"]}~${number}~${number}`;

/**
 * We need to encode cell type metadata here, so we can use it in onClick event
 */
export function getAllSerializedCellTypeMetadata(
  cellTypes: CellType[],
  tissue: Tissue
): CellTypeMetadata[] {
  return cellTypes.map(({ viewId, name, order, total_count }) => {
    return `${viewId}~${tissue}~${name}~${order}~${total_count}` as CellTypeMetadata;
  });
}

export function deserializeCellTypeMetadata(
  cellTypeMetadata: CellTypeMetadata
): {
  viewId: CellType["viewId"];
  name: CellType["name"];
  tissue: Tissue;
  order: number;
  total_count: number;
  id: string;
  optionId: OptionId;
} {
  const [rawViewId, tissue, name, order, total_count] = cellTypeMetadata.split(
    TISSUE_CELL_TYPE_DIVIDER
  );

  // (thuang): Typescript limitation that split() returns string[]
  const viewId = rawViewId as CellType["viewId"];

  const id = getOntologyTermIdFromCellTypeViewId(viewId);
  const optionId = getOptionIdFromCellTypeViewId(viewId);

  return {
    id,
    name,
    optionId,
    order: Number(order),
    tissue,
    total_count: Number(total_count),
    viewId,
  };
}

/**
 * Value format: `${name}`
 */
export function getGeneNames(
  genes: ({ name: string } | undefined)[]
): string[] {
  return genes.map((gene) => gene?.name || "");
}

/**
 * This is to add hyphens to tissue names that have spaces so that they can be used properly as an element ID
 */
export function hyphenize(str: string): string {
  return str.replace(/\s+/g, "-");
}
