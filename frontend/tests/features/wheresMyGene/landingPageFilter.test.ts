import { expect, test } from "@playwright/test";
import {
  WMG_WITH_SEEDED_GENES,
  checkPlotSize,
  checkSourceData,
  conditionallyRunTests,
  deSelectSecondaryFilterOption,
  goToWMG,
  selectSecondaryFilterOption,
} from "tests/utils/wmgUtils";
import { goToPage, tryUntil } from "tests/utils/helpers";
import {
  COLOR_SCALE_TOOLTIP_TEXT,
  GROUP_BY_TOOLTIP_TEXT,
  SORT_CELL_TYPES_TOOLTIP_TEXT,
  SORT_GENES_TOOLTIP_TEXT,
} from "src/views/WheresMyGene/common/constants";
import { CELL_TYPE_LABELS_ID } from "tests/common/constants";

const SIDE_BAR_TOGGLE_BUTTON_ID = "side-bar-toggle-button";

const { describe } = test;

describe("Left side bar", () => {
  /**
   * TODO(thuang): Remove forceRun when all WMG e2e tests are enabled.
   * `forceRun` is just to incrementally add tests back in the meantime
   */
  conditionallyRunTests({ forceRun: true });

  test("Left side bar collapse and expand", async ({ page }) => {
    await goToWMG(page);

    // click chevron left to collapse the left tab
    await page.getByTestId(SIDE_BAR_TOGGLE_BUTTON_ID).click();

    // verify the left tab is collapsed
    expect(await page.getByTestId("add-organism").isVisible()).toBeFalsy();
  });

  [
    "dataset-filter",
    "disease-filter",
    "self-reported-ethnicity-filter",
    "sex-filter",
  ].forEach((filterOption) => {
    test(`Should be able select and de-select options for ${filterOption} filter`, async ({
      page,
    }) => {
      await goToPage(WMG_WITH_SEEDED_GENES.URL, page);

      // (thuang): This expands the first tissue
      await page.getByTestId(CELL_TYPE_LABELS_ID).first().click();

      await tryUntil(
        async () => {
          // check the count of source data displayed before adding a filter
          const countBeforeFilter = await checkSourceData(page);

          // verify source data loading some data
          expect(countBeforeFilter).toBeGreaterThan(0);

          // check plot height before adding a filter
          const plotSizeBeforeFilter = await checkPlotSize(page);

          // verify data plot data loading some data
          expect(plotSizeBeforeFilter).toBeGreaterThan(0);

          // select a filter
          await selectSecondaryFilterOption(page, filterOption);

          await tryUntil(
            async () => {
              // check the count of source data displayed after adding a filter
              const countAfterFilter = await checkSourceData(page);

              //check plot height after adding a filter
              const plotSizeAfterFilter = await checkPlotSize(page);

              // verify source data changed after filter is applied
              expect(countBeforeFilter === countAfterFilter).toBeFalsy();

              // verify data plot data changed after filter was applied
              expect(plotSizeBeforeFilter === plotSizeAfterFilter).toBeFalsy();
            },
            { page }
          );

          // uncheck filter
          await deSelectSecondaryFilterOption(page, filterOption);
        },
        {
          page,
          /**
           * (thuang): Give up after N times, because the app state might not
           * be recoverable at this point
           */
          maxRetry: 3,
        }
      );
    });
  });

  test("Left side bar tooltips", async ({ page }) => {
    await goToPage(WMG_WITH_SEEDED_GENES.URL, page);

    // Group By tooltip
    await page.getByTestId("group-by-tooltip-icon").hover();
    expect(page.getByText(GROUP_BY_TOOLTIP_TEXT)).toBeTruthy();

    // Color Scale tooltip
    await page.getByTestId("color-scale-tooltip-icon").hover();
    expect(page.getByText(COLOR_SCALE_TOOLTIP_TEXT)).toBeTruthy();

    // Sort Cell Type tooltip
    await page.getByTestId("sort-cell-types-tooltip-icon").hover();
    expect(page.getByText(SORT_CELL_TYPES_TOOLTIP_TEXT)).toBeTruthy();

    // Sort Gene tooltip
    await page.getByTestId("sort-genes-tooltip-icon").hover();
    expect(page.getByText(SORT_GENES_TOOLTIP_TEXT)).toBeTruthy();
  });
});
