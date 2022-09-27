import Step from "./components/Step";
import {
  ColumnOne,
  ColumnTwo,
  StyledStepOne,
  StyledStepThree,
  StyledStepTwo,
  Wrapper,
} from "./style";

interface Props {
  tissueSelected: boolean;
  isLoading: boolean;
  geneSelected: boolean;
}

let tissueHasLoadedOnce = false;
let geneHasLoadedOnce = false;

export default function GetStarted({
  tissueSelected,
  isLoading,
  geneSelected,
}: Props): JSX.Element {
  if (!tissueHasLoadedOnce && tissueSelected && !isLoading) {
    tissueHasLoadedOnce = true;
  }
  if (!geneHasLoadedOnce && geneSelected && !isLoading) {
    geneHasLoadedOnce = true;
  }
  return (
    <Wrapper
      style={
        tissueHasLoadedOnce && geneHasLoadedOnce ? { display: "none" } : {}
      }
    >
      <ColumnOne style={tissueHasLoadedOnce ? { visibility: "hidden" } : {}}>
        <StyledStepOne>
          <Step step={1} details="Add Tissues" />
        </StyledStepOne>
      </ColumnOne>

      <ColumnTwo style={geneHasLoadedOnce ? { visibility: "hidden" } : {}}>
        <StyledStepTwo>
          <Step step={2} details="Add Genes" />
        </StyledStepTwo>
        <StyledStepThree>
          <Step step={3} details="Explore Gene Expression" />
        </StyledStepThree>
      </ColumnTwo>
    </Wrapper>
  );
}
