import {
  DialogActions,
  DialogContent,
  DialogPaper,
  DialogTitle,
  fontBodyXs,
  fontHeaderL,
} from "@czi-sds/components";
import styled from "@emotion/styled";
import { spacesDefault, spacesXl, spacesXxs } from "src/common/theme";

export const StyledDialogTitle = styled(DialogTitle)`
  ${fontHeaderL}
  margin-bottom: ${spacesDefault}px;
`;

/**
 * (thuang): SDS DialogTitle currently doesn't support
 * swapping out their Title component, so this is a workaround
 */
export const Title = styled("p")`
  ${fontHeaderL}
`;

export const StyledDialogPaper = styled(DialogPaper)`
  padding: ${spacesXl}px !important;
`;

export const StyledDialogContent = styled(DialogContent)`
  ${fontBodyXs}
`;

/**
 * (thuang): We want the word to word space between buttons to be
 * 16px, so reducing margin-left to spacesXxs gives us that
 */
export const StyledDialogAction = styled(DialogActions)`
  .MuiButton-text {
    min-width: 64px; /* (mcdade): reinstated min-width to SDS minimal button to maintain the desired word to word space as per (thuang) above */
  }

  &.MuiDialogActions-spacing > :not(:first-of-type) {
    margin-left: ${spacesXxs}px;
  }
`;
