import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ProviderSettings } from "../../../src/components/settings/ProviderSettings";
import { api } from "../../../src/api/client";
import { makeSecretStatus, makeSettings, renderWithClient } from "../../helpers";

jest.mock("../../../src/api/client", () => ({
  api: {
    getSettings: jest.fn(),
    updateSettings: jest.fn(),
    setSecret: jest.fn(),
    clearSecret: jest.fn(),
  },
}));

const mockedGet = api.getSettings as jest.MockedFunction<typeof api.getSettings>;
const mockedUpdate = api.updateSettings as jest.MockedFunction<typeof api.updateSettings>;
const mockedSet = api.setSecret as jest.MockedFunction<typeof api.setSecret>;

beforeEach(() => {
  jest.clearAllMocks();
  mockedGet.mockResolvedValue(
    makeSettings({
      secrets: [
        makeSecretStatus({ name: "openai_api_key", masked: "1234", overridden: true }),
        makeSecretStatus({ name: "anthropic_api_key", configured: false, masked: "" }),
        makeSecretStatus({ name: "gemini_api_key", masked: "9zZ0" }),
      ],
    }),
  );
  mockedUpdate.mockResolvedValue(makeSettings());
  mockedSet.mockResolvedValue(makeSecretStatus());
});

describe("<ProviderSettings>", () => {
  it("shows masked keys and a differs-from-.env badge, never a full key", async () => {
    renderWithClient(<ProviderSettings />);
    const openai = await screen.findByTestId("secret-openai_api_key");

    expect(within(openai).getByText("••••1234")).toBeInTheDocument();
    expect(within(openai).getByText(/differs from .env/i)).toBeInTheDocument();
    // The replace field is a password input that never carries a value.
    const input = within(openai).getByLabelText(/Replace OpenAI API key/i);
    expect(input).toHaveAttribute("type", "password");
    expect(input).toHaveValue("");
  });

  it("replaces a secret through the write-only field", async () => {
    renderWithClient(<ProviderSettings />);
    const openai = await screen.findByTestId("secret-openai_api_key");

    await userEvent.type(within(openai).getByLabelText(/Replace OpenAI API key/i), "sk-new");
    await userEvent.click(within(openai).getByRole("button", { name: "Replace" }));

    expect(mockedSet).toHaveBeenCalledWith("openai_api_key", "sk-new");
  });

  it("saves the provider settings", async () => {
    renderWithClient(<ProviderSettings />);
    await screen.findByTestId("provider-settings");

    await userEvent.click(screen.getByRole("button", { name: /Save provider settings/ }));
    await waitFor(() => expect(mockedUpdate).toHaveBeenCalled());
  });

  it("renders exactly two provider radios; the .env provider is checked", async () => {
    renderWithClient(<ProviderSettings />);
    await screen.findByTestId("provider-settings");

    const group = screen.getByRole("radiogroup", { name: "Provider" });
    const radios = within(group).getAllByRole("radio");
    expect(radios).toHaveLength(2);
    expect(within(group).getByRole("radio", { name: /OpenAI/ })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    expect(within(group).getByRole("radio", { name: /Anthropic/ })).toHaveAttribute(
      "aria-checked",
      "false",
    );
  });

  it("selecting Anthropic then saving sends evaluatorProvider: anthropic", async () => {
    renderWithClient(<ProviderSettings />);
    await screen.findByTestId("provider-settings");

    const group = screen.getByRole("radiogroup", { name: "Provider" });
    await userEvent.click(within(group).getByRole("radio", { name: /Anthropic/ }));
    await userEvent.click(screen.getByRole("button", { name: /Save provider settings/ }));

    await waitFor(() => expect(mockedUpdate).toHaveBeenCalled());
    expect(mockedUpdate).toHaveBeenCalledWith(
      expect.objectContaining({ evaluatorProvider: "anthropic" }),
    );
  });

  it("renders the Default badge on the envDefaults provider card", async () => {
    mockedGet.mockResolvedValue(
      makeSettings({
        evaluatorProvider: "anthropic",
        envDefaults: {
          evaluatorProvider: "anthropic",
          evaluatorModel: null,
          scheduleCron: "0 8 * * 1-5",
          scheduleTimezone: "UTC",
          enrichmentMode: "shadow",
          voice: { tone: "direct", person: "first_person", styleNotes: "" },
        },
      }),
    );
    renderWithClient(<ProviderSettings />);
    const group = await screen.findByRole("radiogroup", { name: "Provider" });

    const anthropic = within(group).getByRole("radio", { name: /Anthropic/ });
    expect(within(anthropic).getByText("Default")).toBeInTheDocument();
    const openai = within(group).getByRole("radio", { name: /OpenAI/ });
    expect(within(openai).queryByText("Default")).not.toBeInTheDocument();
  });

  it("renders the configured token rates on the OpenAI card", async () => {
    renderWithClient(<ProviderSettings />);
    const group = await screen.findByRole("radiogroup", { name: "Provider" });

    const openai = within(group).getByRole("radio", { name: /OpenAI/ });
    expect(within(openai).getByText(/\$2\.50 \/ \$10\.00/)).toBeInTheDocument();
  });

  it("switches the pre-filter mode and saves the new enrichmentMode", async () => {
    renderWithClient(<ProviderSettings />);
    await screen.findByTestId("provider-settings");

    const group = screen.getByRole("radiogroup", { name: "Pre-filter mode" });
    expect(within(group).getByRole("radio", { name: /Shadow/ })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    await userEvent.click(within(group).getByRole("radio", { name: /Enforce/ }));
    await userEvent.click(screen.getByRole("button", { name: /Save provider settings/ }));

    await waitFor(() => expect(mockedUpdate).toHaveBeenCalled());
    expect(mockedUpdate).toHaveBeenCalledWith(
      expect.objectContaining({ enrichmentMode: "enforce" }),
    );
  });

  it("never renders a key prefix", async () => {
    const { container } = renderWithClient(<ProviderSettings />);
    await screen.findByTestId("provider-settings");

    expect(container.textContent).not.toContain("sk-");
  });
});
