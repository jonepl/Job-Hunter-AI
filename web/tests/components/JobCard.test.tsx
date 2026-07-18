import { render, screen } from "@testing-library/react";

import { JobCard } from "../../src/components/JobCard";
import { makeJob } from "../helpers";

describe("<JobCard>", () => {
  it("renders the job's identity, providers, and score", () => {
    render(
      <JobCard
        job={makeJob({
          title: "Staff Engineer",
          company: "Northwind",
          location: "Remote",
          platforms: ["linkedin", "indeed"],
          score: 82,
        })}
      />,
    );

    expect(screen.getByText("Staff Engineer")).toBeInTheDocument();
    expect(screen.getByText(/Northwind/)).toBeInTheDocument();
    expect(screen.getByText("via LinkedIn, Indeed")).toBeInTheDocument();
    expect(screen.getByTestId("score-chip")).toHaveAttribute("data-state", "qualify");
    expect(screen.getByTestId("score-chip")).toHaveTextContent("82 · Qualifying");
  });

  it("links the title to the posting when a url is present", () => {
    render(<JobCard job={makeJob({ title: "Linked Role", url: "https://x/42" })} />);
    expect(screen.getByRole("link", { name: "Linked Role" })).toHaveAttribute(
      "href",
      "https://x/42",
    );
  });
});
