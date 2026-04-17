/**
 * Profile page – Client component tests
 *
 * Contracts guarded:
 * 1. ProfilePageClient renders the "Default Addresses" section and addresses list
 * 2. AddressDialog submit calls createAddress and shows success toast
 * 3. DefaultAddressesCard shipping select change triggers updateProfile PATCH call
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../helpers/render";
import { createRouterMock } from "../helpers/nextNavigation";
import type { AccountDto, AddressDto, ProfileDto } from "@/lib/api/profile";

// ── Module mocks ──────────────────────────────────────────────────────────────

const mockRouter = createRouterMock();

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
  usePathname: () => "/profile",
}));

const mockCreateAddress = vi.fn();
const mockUpdateAddress = vi.fn();
const mockUpdateProfile = vi.fn();
const mockDeleteAddress = vi.fn();
const mockPatchAccount = vi.fn();

vi.mock("@/lib/api/profile", () => ({
  createAddress: (...args: unknown[]) => mockCreateAddress(...args),
  updateAddress: (...args: unknown[]) => mockUpdateAddress(...args),
  updateProfile: (...args: unknown[]) => mockUpdateProfile(...args),
  deleteAddress: (...args: unknown[]) => mockDeleteAddress(...args),
  patchAccount: (...args: unknown[]) => mockPatchAccount(...args),
}));

vi.mock("@/components/auth/AuthProvider", () => ({
  useAuth: () => ({ refresh: vi.fn().mockResolvedValue({}) }),
}));

const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();

vi.mock("sonner", () => ({
  toast: {
    success: (...args: unknown[]) => mockToastSuccess(...args),
    error: (...args: unknown[]) => mockToastError(...args),
  },
}));

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeAccount(overrides?: Partial<AccountDto>): AccountDto {
  return {
    email: "user@example.com",
    first_name: "Alice",
    last_name: "Smith",
    ...overrides,
  };
}

function makeProfile(overrides?: Partial<ProfileDto>): ProfileDto {
  return {
    id: 1,
    default_shipping_address: null,
    default_billing_address: null,
    ...overrides,
  };
}

function makeAddress(overrides?: Partial<AddressDto>): AddressDto {
  return {
    id: 1,
    first_name: "John",
    last_name: "Doe",
    street_line_1: "Main Street 1",
    street_line_2: "",
    city: "Prague",
    postal_code: "11000",
    country: "CZ",
    company: "",
    vat_id: "",
    phone: "+420123456789",
    ...overrides,
  };
}

// ── Test suite ────────────────────────────────────────────────────────────────

describe("ProfilePageClient", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the Default Addresses section and addresses list", async () => {
    const user = userEvent.setup();
    const { default: ProfilePageClient } =
      await import("@/components/profile/ProfilePageClient");
    const addresses = [
      makeAddress({ id: 1, street_line_1: "A 1" }),
      makeAddress({ id: 2, street_line_1: "A 2" }),
    ];

    renderWithProviders(
      <ProfilePageClient
        account={makeAccount()}
        emailVerified={true}
        profile={makeProfile()}
        addresses={addresses}
        initialTab="account"
        showEmailChangeCancelledToast={false}
      />,
    );

    // Switch to the Addresses tab
    await user.click(screen.getByRole("tab", { name: /addresses/i }));

    expect(screen.getByText("Default Addresses")).toBeInTheDocument();
    expect(screen.getByTestId("address-list")).toBeInTheDocument();
    expect(screen.getByTestId("address-item-1")).toBeInTheDocument();
    expect(screen.getByTestId("address-item-2")).toBeInTheDocument();
  });

  it("renders empty state when there are no addresses", async () => {
    const user = userEvent.setup();
    const { default: ProfilePageClient } =
      await import("@/components/profile/ProfilePageClient");

    renderWithProviders(
      <ProfilePageClient
        account={makeAccount()}
        emailVerified={true}
        profile={makeProfile()}
        addresses={[]}
        initialTab="account"
        showEmailChangeCancelledToast={false}
      />,
    );

    // Switch to the Addresses tab
    await user.click(screen.getByRole("tab", { name: /addresses/i }));

    expect(screen.getByText(/no addresses saved/i)).toBeInTheDocument();
  });
});

describe("AddressDialog – create mode", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("submit calls createAddress and shows success toast on success", async () => {
    const { AddressDialog } =
      await import("@/components/profile/AddressDialog");
    const user = userEvent.setup();
    mockCreateAddress.mockResolvedValue({ id: 99 });
    const onSaved = vi.fn();

    renderWithProviders(
      <AddressDialog
        open
        initial={null}
        onOpenChange={vi.fn()}
        onSaved={onSaved}
      />,
    );

    await user.type(screen.getByLabelText(/first name/i), "Jane");
    await user.type(screen.getByLabelText(/last name/i), "Doe");
    await user.type(screen.getByLabelText(/street/i), "Oak Avenue 5");
    await user.type(screen.getByLabelText(/postal code/i), "10000");
    await user.type(screen.getByLabelText(/city/i), "Brno");
    await user.type(screen.getByLabelText(/phone/i), "+420777111222");
    // Country defaults to "CZ" in CountryPicker — no user interaction needed.

    await user.click(screen.getByTestId("address-dialog-submit"));

    await waitFor(() => {
      expect(mockCreateAddress).toHaveBeenCalledWith(
        expect.objectContaining({
          first_name: "Jane",
          last_name: "Doe",
          city: "Brno",
          phone: "+420777111222",
        }),
      );
    });

    await waitFor(() => {
      expect(mockToastSuccess).toHaveBeenCalledWith("Address added.");
    });

    expect(onSaved).toHaveBeenCalledTimes(1);
  });

  it("shows error toast when createAddress rejects", async () => {
    const { AddressDialog } =
      await import("@/components/profile/AddressDialog");
    const user = userEvent.setup();
    mockCreateAddress.mockRejectedValue(new Error("network fail"));

    renderWithProviders(
      <AddressDialog
        open
        initial={null}
        onOpenChange={vi.fn()}
        onSaved={vi.fn()}
      />,
    );

    await user.type(screen.getByLabelText(/first name/i), "Jane");
    await user.type(screen.getByLabelText(/last name/i), "Doe");
    await user.type(screen.getByLabelText(/street/i), "Oak Avenue 5");
    await user.type(screen.getByLabelText(/postal code/i), "10000");
    await user.type(screen.getByLabelText(/city/i), "Brno");
    await user.type(screen.getByLabelText(/phone/i), "+420000000000");
    // Country defaults to "CZ" in CountryPicker — no user interaction needed.

    await user.click(screen.getByTestId("address-dialog-submit"));

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith("Failed to save address.");
    });
  });
});

describe("AddressDialog – submit payload", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sends first_name and last_name (not full_name) in the create payload", async () => {
    const { AddressDialog } =
      await import("@/components/profile/AddressDialog");
    const user = userEvent.setup();
    mockCreateAddress.mockResolvedValue({ id: 42 });

    renderWithProviders(
      <AddressDialog
        open
        initial={null}
        onOpenChange={vi.fn()}
        onSaved={vi.fn()}
      />,
    );

    await user.type(screen.getByLabelText(/first name/i), "Alice");
    await user.type(screen.getByLabelText(/last name/i), "Smith");
    await user.type(screen.getByLabelText(/street/i), "Elm St 7");
    await user.type(screen.getByLabelText(/postal code/i), "60200");
    await user.type(screen.getByLabelText(/city/i), "Brno");
    await user.type(screen.getByLabelText(/phone/i), "+420111222333");
    // Country defaults to "CZ" in CountryPicker — no user interaction needed.

    await user.click(screen.getByTestId("address-dialog-submit"));

    await waitFor(() => {
      expect(mockCreateAddress).toHaveBeenCalledTimes(1);
    });

    const calledWith = mockCreateAddress.mock.calls[0][0];
    // Must use split fields, never the legacy full_name key
    expect(calledWith).toHaveProperty("first_name", "Alice");
    expect(calledWith).toHaveProperty("last_name", "Smith");
    expect(calledWith).not.toHaveProperty("full_name");
  });
});

describe("AddressDialog – phone field", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders a phone input field", async () => {
    const { AddressDialog } =
      await import("@/components/profile/AddressDialog");

    renderWithProviders(
      <AddressDialog
        open
        initial={null}
        onOpenChange={vi.fn()}
        onSaved={vi.fn()}
      />,
    );

    const phoneInput = screen.getByLabelText(/phone/i);
    expect(phoneInput).toBeInTheDocument();
  });

  it("phone input has the required attribute", async () => {
    const { AddressDialog } =
      await import("@/components/profile/AddressDialog");

    renderWithProviders(
      <AddressDialog
        open
        initial={null}
        onOpenChange={vi.fn()}
        onSaved={vi.fn()}
      />,
    );

    const phoneInput = screen.getByLabelText(/phone/i);
    expect(phoneInput).toBeRequired();
  });

  it("populates phone from initial address in edit mode", async () => {
    const { AddressDialog } =
      await import("@/components/profile/AddressDialog");

    renderWithProviders(
      <AddressDialog
        open
        initial={makeAddress({ phone: "+420987654321" })}
        onOpenChange={vi.fn()}
        onSaved={vi.fn()}
      />,
    );

    const phoneInput = screen.getByLabelText(/phone/i) as HTMLInputElement;
    expect(phoneInput.value).toBe("+420987654321");
  });

  it("includes phone in the create payload", async () => {
    const { AddressDialog } =
      await import("@/components/profile/AddressDialog");
    const user = userEvent.setup();
    mockCreateAddress.mockResolvedValue({ id: 55 });

    renderWithProviders(
      <AddressDialog
        open
        initial={null}
        onOpenChange={vi.fn()}
        onSaved={vi.fn()}
      />,
    );

    await user.type(screen.getByLabelText(/first name/i), "Test");
    await user.type(screen.getByLabelText(/last name/i), "User");
    await user.type(screen.getByLabelText(/street/i), "Test Street 1");
    await user.type(screen.getByLabelText(/postal code/i), "10000");
    await user.type(screen.getByLabelText(/city/i), "Prague");
    await user.type(screen.getByLabelText(/phone/i), "+420555444333");

    await user.click(screen.getByTestId("address-dialog-submit"));

    await waitFor(() => {
      expect(mockCreateAddress).toHaveBeenCalledWith(
        expect.objectContaining({ phone: "+420555444333" }),
      );
    });
  });
});

describe("DefaultAddressesCard – set default address", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("changing default shipping select fires updateProfile with the correct ID", async () => {
    const { DefaultAddressesCard } =
      await import("@/components/profile/DefaultAddressesCard");
    const user = userEvent.setup();
    mockUpdateProfile.mockResolvedValue({});

    const addresses = [
      makeAddress({
        id: 1,
        first_name: "John",
        last_name: "Doe",
        street_line_1: "A1",
        city: "Prague",
      }),
      makeAddress({
        id: 2,
        first_name: "Jane",
        last_name: "Doe",
        street_line_1: "B2",
        city: "Brno",
      }),
    ];

    renderWithProviders(
      <DefaultAddressesCard profile={makeProfile()} addresses={addresses} />,
    );

    const select = screen.getByTestId("select-default-shipping");
    await user.selectOptions(select, "1");

    await waitFor(() => {
      expect(mockUpdateProfile).toHaveBeenCalledWith({
        default_shipping_address: 1,
      });
    });

    await waitFor(() => {
      expect(mockToastSuccess).toHaveBeenCalledWith("Default address updated.");
    });
  });

  it("changing default billing select fires updateProfile with the correct ID", async () => {
    const { DefaultAddressesCard } =
      await import("@/components/profile/DefaultAddressesCard");
    const user = userEvent.setup();
    mockUpdateProfile.mockResolvedValue({});

    const addresses = [
      makeAddress({
        id: 3,
        first_name: "Ann",
        last_name: "Other",
        street_line_1: "C3",
        city: "Ostrava",
      }),
    ];

    renderWithProviders(
      <DefaultAddressesCard profile={makeProfile()} addresses={addresses} />,
    );

    const select = screen.getByTestId("select-default-billing");
    await user.selectOptions(select, "3");

    await waitFor(() => {
      expect(mockUpdateProfile).toHaveBeenCalledWith({
        default_billing_address: 3,
      });
    });
  });
});
