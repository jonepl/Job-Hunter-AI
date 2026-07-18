import { render, screen } from "@testing-library/react";

import { ProviderBadges } from "../../src/components/ProviderBadges";

describe("<ProviderBadges>", () => {
  it("renders the whole set inline, never assuming length 1", () => {
    render(<ProviderBadges platforms={["linkedin", "indeed"]} variant="inline" />);
    expect(screen.getByText("via LinkedIn, Indeed")).toBeInTheDocument();
  });

  it("renders each platform as a badge in the badges variant", () => {
    render(<ProviderBadges platforms={["linkedin", "indeed"]} variant="badges" />);
    expect(screen.getByText("LinkedIn")).toBeInTheDocument();
    expect(screen.getByText("Indeed")).toBeInTheDocument();
  });

  it("renders nothing when there are no platforms", () => {
    const { container } = render(<ProviderBadges platforms={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
