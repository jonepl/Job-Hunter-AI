import { scoreState } from "../../src/lib/score";

// threshold 70, near-miss floor 55 → band is [55, 70).
describe("scoreState (ADR-033 boundaries)", () => {
  it("qualifies at exactly the threshold", () => {
    expect(scoreState(70, 70, 55)).toBe("qualify");
  });

  it("qualifies above the threshold", () => {
    expect(scoreState(91, 70, 55)).toBe("qualify");
  });

  it("is near-miss just below the threshold", () => {
    expect(scoreState(69, 70, 55)).toBe("nearmiss");
  });

  it("is near-miss at exactly the floor", () => {
    expect(scoreState(55, 70, 55)).toBe("nearmiss");
  });

  it("is below just under the floor", () => {
    expect(scoreState(54, 70, 55)).toBe("below");
  });

  it("treats a missing score as below", () => {
    expect(scoreState(null, 70, 55)).toBe("below");
  });

  it("treats a missing threshold as below", () => {
    expect(scoreState(82, null, 55)).toBe("below");
  });
});
