"use client";

import * as React from "react";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Truck,
  CreditCard,
  Banknote,
} from "lucide-react";

import { cn } from "@/lib/utils";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Checkbox } from "@/components/ui/checkbox";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { CheckoutPriceChangeBanner } from "@/components/checkout/CheckoutPriceChangeBanner";
import { CountryPicker } from "@/components/ui/country-picker";
import type { PriceChangePayload } from "@/lib/api/checkout";

// Types
export interface CheckoutValues {
  // Step 1: Shipping & Payment methods (placeholders)
  shipping_method: string;
  payment_method: string;
  // Step 2: Customer info
  customer_email: string;
  // Shipping address
  shipping_first_name: string;
  shipping_last_name: string;
  shipping_company: string;
  shipping_company_id: string;
  shipping_vat_id: string;
  shipping_address_line1: string;
  shipping_address_line2: string;
  shipping_city: string;
  shipping_postal_code: string;
  shipping_country: string;
  shipping_phone: string;
  // Billing
  billing_same_as_shipping: boolean;
  billing_first_name: string;
  billing_last_name: string;
  billing_company: string;
  billing_company_id: string;
  billing_vat_id: string;
  billing_address_line1: string;
  billing_address_line2: string;
  billing_city: string;
  billing_postal_code: string;
  billing_country: string;
  billing_phone: string;
  // Profile save (only relevant for authenticated users)
  save_to_profile: boolean;
}

interface CheckoutFormProps {
  initialValues?: Partial<CheckoutValues>;
  onSubmit: (values: CheckoutValues) => Promise<void>;
  onBackToCart: () => void;
  onContinueShopping?: () => void;
  /**
   * When provided and severity is WARNING, renders the price-change banner
   * inside Step 1 (before shipping method cards).  Not shown in Step 2.
   */
  priceChangePayload?: PriceChangePayload | null;
  /** When true, the "Save addresses to my profile" checkbox is shown in Step 2. */
  isAuthenticated?: boolean;
}

type FieldErrors = Partial<Record<keyof CheckoutValues, string>>;

const defaultValues: CheckoutValues = {
  shipping_method: "STANDARD",
  payment_method: "CARD",
  customer_email: "",
  shipping_first_name: "",
  shipping_last_name: "",
  shipping_company: "",
  shipping_company_id: "",
  shipping_vat_id: "",
  shipping_address_line1: "",
  shipping_address_line2: "",
  shipping_city: "",
  shipping_postal_code: "",
  shipping_country: "",
  shipping_phone: "",
  billing_same_as_shipping: true,
  billing_first_name: "",
  billing_last_name: "",
  billing_company: "",
  billing_company_id: "",
  billing_vat_id: "",
  billing_address_line1: "",
  billing_address_line2: "",
  billing_city: "",
  billing_postal_code: "",
  billing_country: "",
  billing_phone: "",
  save_to_profile: true,
};

// Stepper component
function StepIndicator({ currentStep }: { currentStep: 1 | 2 }) {
  const steps = [
    { step: 1, label: "Shipping & Payment" },
    { step: 2, label: "Details" },
  ];

  return (
    <div className="flex items-center justify-center gap-2">
      {steps.map((s, index) => (
        <React.Fragment key={s.step}>
          <div className="flex items-center gap-2">
            <div
              className={cn(
                "flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium transition-colors",
                currentStep === s.step
                  ? "bg-primary text-primary-foreground"
                  : currentStep > s.step
                    ? "bg-primary/20 text-primary"
                    : "bg-muted text-muted-foreground",
              )}
            >
              {currentStep > s.step ? <Check className="h-4 w-4" /> : s.step}
            </div>
            <span
              className={cn(
                "text-sm font-medium hidden sm:inline",
                currentStep === s.step
                  ? "text-foreground"
                  : "text-muted-foreground",
              )}
            >
              {s.label}
            </span>
          </div>
          {index < steps.length - 1 && <Separator className="w-8 sm:w-16" />}
        </React.Fragment>
      ))}
    </div>
  );
}

// Form field component with error handling
function FormField({
  id,
  label,
  required,
  error,
  children,
}: {
  id: string;
  label: string;
  required?: boolean;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id}>
        {label}
        {required && <span className="text-destructive ml-0.5">*</span>}
      </Label>
      {children}
      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

// Step 1: Shipping & Payment selection
function ShippingPaymentStep({
  values,
  onChange,
  onBack,
  onContinue,
  priceChangePayload,
}: {
  values: CheckoutValues;
  onChange: (field: keyof CheckoutValues, value: string | boolean) => void;
  onBack: () => void;
  onContinue: () => void;
  priceChangePayload?: PriceChangePayload | null;
}) {
  return (
    <div className="flex flex-col gap-6">
      {/* Price-change warning banner — only shown when prices changed since add-to-cart */}
      {priceChangePayload?.severity === "WARNING" && (
        <CheckoutPriceChangeBanner
          payload={priceChangePayload}
          onBackToCart={onBack}
        />
      )}

      {/* Shipping Method */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Truck className="h-5 w-5" />
            Shipping Method
          </CardTitle>
          <CardDescription>
            Choose how you'd like your order delivered
          </CardDescription>
        </CardHeader>
        <CardContent>
          <RadioGroup
            value={values.shipping_method}
            onValueChange={(val) => onChange("shipping_method", val)}
            aria-label="Shipping method"
          >
            <div className="flex flex-col gap-3">
              <label
                className={cn(
                  "flex cursor-pointer items-center gap-4 rounded-lg border p-4 transition-colors",
                  values.shipping_method === "STANDARD"
                    ? "border-primary bg-primary/5"
                    : "border-border hover:bg-muted/50",
                )}
              >
                <RadioGroupItem value="STANDARD" id="shipping-standard" />
                <div className="flex flex-1 flex-col gap-0.5">
                  <span className="font-medium text-foreground">
                    Standard (3-5 days)
                  </span>
                  <span className="text-sm text-muted-foreground">
                    Free shipping on all orders
                  </span>
                </div>
                <span className="font-semibold text-foreground">$0.00</span>
              </label>
              <label
                className={cn(
                  "flex cursor-pointer items-center gap-4 rounded-lg border p-4 transition-colors",
                  values.shipping_method === "EXPRESS"
                    ? "border-primary bg-primary/5"
                    : "border-border hover:bg-muted/50",
                )}
              >
                <RadioGroupItem value="EXPRESS" id="shipping-express" />
                <div className="flex flex-1 flex-col gap-0.5">
                  <span className="font-medium text-foreground">
                    Express (1-2 days)
                  </span>
                  <span className="text-sm text-muted-foreground">
                    Priority handling and delivery
                  </span>
                </div>
                <span className="font-semibold text-foreground">$9.99</span>
              </label>
            </div>
          </RadioGroup>
        </CardContent>
      </Card>

      {/* Payment Method */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <CreditCard className="h-5 w-5" />
            Payment Method
          </CardTitle>
          <CardDescription>
            Select your preferred payment option
          </CardDescription>
        </CardHeader>
        <CardContent>
          <RadioGroup
            value={values.payment_method}
            onValueChange={(val) => onChange("payment_method", val)}
            aria-label="Payment method"
          >
            <div className="flex flex-col gap-3">
              <label
                className={cn(
                  "flex cursor-pointer items-center gap-4 rounded-lg border p-4 transition-colors",
                  values.payment_method === "CARD"
                    ? "border-primary bg-primary/5"
                    : "border-border hover:bg-muted/50",
                )}
              >
                <RadioGroupItem value="CARD" id="payment-card" />
                <CreditCard className="h-5 w-5 text-muted-foreground" />
                <div className="flex flex-1 flex-col gap-0.5">
                  <span className="font-medium text-foreground">
                    Card (simulated)
                  </span>
                  <span className="text-sm text-muted-foreground">
                    Pay securely with your credit or debit card
                  </span>
                </div>
              </label>
              <label
                className={cn(
                  "flex cursor-pointer items-center gap-4 rounded-lg border p-4 transition-colors",
                  values.payment_method === "COD"
                    ? "border-primary bg-primary/5"
                    : "border-border hover:bg-muted/50",
                )}
              >
                <RadioGroupItem value="COD" id="payment-cod" />
                <Banknote className="h-5 w-5 text-muted-foreground" />
                <div className="flex flex-1 flex-col gap-0.5">
                  <span className="font-medium text-foreground">
                    Cash on delivery (simulated)
                  </span>
                  <span className="text-sm text-muted-foreground">
                    Pay when you receive your order
                  </span>
                </div>
              </label>
            </div>
          </RadioGroup>
        </CardContent>
      </Card>

      {/* Demo Note */}
      <p className="text-center text-sm text-muted-foreground">
        Shipping and payment are simulated in this demo.
      </p>

      {/* Actions */}
      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
        <Button
          variant="outline"
          onClick={onBack}
          className="gap-2 bg-transparent"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to cart
        </Button>
        <Button
          data-testid="checkout-continue"
          onClick={onContinue}
          className="gap-2"
        >
          Continue
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

// Step 2: Customer & Address details
function DetailsStep({
  values,
  errors,
  onChange,
  onBack,
  onSubmit,
  firstErrorRef,
  isAuthenticated,
  isSubmitting,
}: {
  values: CheckoutValues;
  errors: FieldErrors;
  onChange: (field: keyof CheckoutValues, value: string | boolean) => void;
  onBack: () => void;
  onSubmit: () => void;
  firstErrorRef: React.RefObject<HTMLInputElement | null>;
  isAuthenticated?: boolean;
  isSubmitting?: boolean;
}) {
  const getInputRef = (field: keyof CheckoutValues) => {
    // Return ref for the first error field
    const errorFields = Object.keys(errors) as (keyof CheckoutValues)[];
    if (errorFields.length > 0 && errorFields[0] === field) {
      return firstErrorRef;
    }
    return undefined;
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Customer Email */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Contact Information</CardTitle>
        </CardHeader>
        <CardContent>
          <FormField
            id="customer_email"
            label="Email address"
            required
            error={errors.customer_email}
          >
            <Input
              name="customer_email"
              id="customer_email"
              type="email"
              placeholder="you@example.com"
              defaultValue={values.customer_email}
              onChange={(e) => onChange("customer_email", e.target.value)}
              aria-invalid={!!errors.customer_email}
              ref={getInputRef("customer_email")}
            />
          </FormField>
        </CardContent>
      </Card>

      {/* Shipping Address */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Shipping Address</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              id="shipping_first_name"
              label="First name"
              required
              error={errors.shipping_first_name}
            >
              <Input
                name="shipping_first_name"
                id="shipping_first_name"
                type="text"
                placeholder="John"
                defaultValue={values.shipping_first_name}
                onChange={(e) =>
                  onChange("shipping_first_name", e.target.value)
                }
                aria-invalid={!!errors.shipping_first_name}
                ref={getInputRef("shipping_first_name")}
              />
            </FormField>
            <FormField
              id="shipping_last_name"
              label="Last name"
              required
              error={errors.shipping_last_name}
            >
              <Input
                name="shipping_last_name"
                id="shipping_last_name"
                type="text"
                placeholder="Doe"
                defaultValue={values.shipping_last_name}
                onChange={(e) => onChange("shipping_last_name", e.target.value)}
                aria-invalid={!!errors.shipping_last_name}
                ref={getInputRef("shipping_last_name")}
              />
            </FormField>
            <div className="sm:col-span-2">
              <FormField id="shipping_company" label="Company (optional)">
                <Input
                  name="shipping_company"
                  id="shipping_company"
                  type="text"
                  placeholder="Acme Corp"
                  defaultValue={values.shipping_company}
                  onChange={(e) => onChange("shipping_company", e.target.value)}
                />
              </FormField>
            </div>
            <div className="sm:col-span-2">
              <FormField id="shipping_company_id" label="Company ID (optional)">
                <Input
                  name="shipping_company_id"
                  id="shipping_company_id"
                  type="text"
                  placeholder="Business / trade registration number"
                  defaultValue={values.shipping_company_id}
                  onChange={(e) =>
                    onChange("shipping_company_id", e.target.value)
                  }
                />
              </FormField>
            </div>
            <div className="sm:col-span-2">
              <FormField id="shipping_vat_id" label="VAT ID (optional)">
                <Input
                  name="shipping_vat_id"
                  id="shipping_vat_id"
                  type="text"
                  placeholder="EU123456789"
                  defaultValue={values.shipping_vat_id}
                  onChange={(e) => onChange("shipping_vat_id", e.target.value)}
                />
              </FormField>
            </div>
            <div className="sm:col-span-2">
              <FormField
                id="shipping_address_line1"
                label="Address line 1"
                required
                error={errors.shipping_address_line1}
              >
                <Input
                  name="shipping_address_line1"
                  id="shipping_address_line1"
                  type="text"
                  placeholder="123 Main Street"
                  defaultValue={values.shipping_address_line1}
                  onChange={(e) =>
                    onChange("shipping_address_line1", e.target.value)
                  }
                  aria-invalid={!!errors.shipping_address_line1}
                  ref={getInputRef("shipping_address_line1")}
                />
              </FormField>
            </div>
            <div className="sm:col-span-2">
              <FormField id="shipping_address_line2" label="Address line 2">
                <Input
                  name="shipping_address_line2"
                  id="shipping_address_line2"
                  type="text"
                  placeholder="Apt, suite, unit (optional)"
                  defaultValue={values.shipping_address_line2}
                  onChange={(e) =>
                    onChange("shipping_address_line2", e.target.value)
                  }
                />
              </FormField>
            </div>
            <FormField
              id="shipping_city"
              label="City"
              required
              error={errors.shipping_city}
            >
              <Input
                name="shipping_city"
                id="shipping_city"
                type="text"
                placeholder="New York"
                defaultValue={values.shipping_city}
                onChange={(e) => onChange("shipping_city", e.target.value)}
                aria-invalid={!!errors.shipping_city}
                ref={getInputRef("shipping_city")}
              />
            </FormField>
            <FormField
              id="shipping_postal_code"
              label="Postal code"
              required
              error={errors.shipping_postal_code}
            >
              <Input
                id="shipping_postal_code"
                name="shipping_postal_code"
                type="text"
                placeholder="10001"
                defaultValue={values.shipping_postal_code}
                onChange={(e) =>
                  onChange("shipping_postal_code", e.target.value)
                }
                aria-invalid={!!errors.shipping_postal_code}
                ref={getInputRef("shipping_postal_code")}
              />
            </FormField>
            <FormField
              id="shipping_country"
              label="Country"
              required
              error={errors.shipping_country}
            >
              <CountryPicker
                name="shipping_country"
                defaultValue={values.shipping_country}
                onChange={(code) => onChange("shipping_country", code)}
              />
            </FormField>
            <FormField
              id="shipping_phone"
              label="Phone number"
              required
              error={errors.shipping_phone}
            >
              <Input
                id="shipping_phone"
                name="shipping_phone"
                type="tel"
                placeholder="+1 (555) 123-4567"
                defaultValue={values.shipping_phone}
                onChange={(e) => onChange("shipping_phone", e.target.value)}
                aria-invalid={!!errors.shipping_phone}
                ref={getInputRef("shipping_phone")}
              />
            </FormField>
          </div>
        </CardContent>
      </Card>

      {/* Billing Address */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Billing Address</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <label className="flex cursor-pointer items-center gap-3">
            <Checkbox
              id="billing_same_as_shipping"
              checked={values.billing_same_as_shipping}
              onCheckedChange={(checked) =>
                onChange("billing_same_as_shipping", checked === true)
              }
            />
            <span className="text-sm font-medium text-foreground">
              Billing address is the same as shipping
            </span>
          </label>

          {!values.billing_same_as_shipping && (
            <div className="grid gap-4 pt-2 sm:grid-cols-2">
              <FormField
                id="billing_first_name"
                label="First name"
                required
                error={errors.billing_first_name}
              >
                <Input
                  id="billing_first_name"
                  name="billing_first_name"
                  type="text"
                  placeholder="John"
                  defaultValue={values.billing_first_name}
                  onChange={(e) =>
                    onChange("billing_first_name", e.target.value)
                  }
                  aria-invalid={!!errors.billing_first_name}
                  ref={getInputRef("billing_first_name")}
                />
              </FormField>
              <FormField
                id="billing_last_name"
                label="Last name"
                required
                error={errors.billing_last_name}
              >
                <Input
                  id="billing_last_name"
                  name="billing_last_name"
                  type="text"
                  placeholder="Doe"
                  defaultValue={values.billing_last_name}
                  onChange={(e) =>
                    onChange("billing_last_name", e.target.value)
                  }
                  aria-invalid={!!errors.billing_last_name}
                  ref={getInputRef("billing_last_name")}
                />
              </FormField>
              <div className="sm:col-span-2">
                <FormField id="billing_company" label="Company (optional)">
                  <Input
                    id="billing_company"
                    name="billing_company"
                    type="text"
                    placeholder="Acme Corp"
                    defaultValue={values.billing_company}
                    onChange={(e) =>
                      onChange("billing_company", e.target.value)
                    }
                  />
                </FormField>
              </div>
              <div className="sm:col-span-2">
                <FormField
                  id="billing_company_id"
                  label="Company ID (optional)"
                >
                  <Input
                    id="billing_company_id"
                    name="billing_company_id"
                    type="text"
                    placeholder="Business / trade registration number"
                    defaultValue={values.billing_company_id}
                    onChange={(e) =>
                      onChange("billing_company_id", e.target.value)
                    }
                  />
                </FormField>
              </div>
              <div className="sm:col-span-2">
                <FormField id="billing_vat_id" label="VAT ID (optional)">
                  <Input
                    id="billing_vat_id"
                    name="billing_vat_id"
                    type="text"
                    placeholder="EU123456789"
                    defaultValue={values.billing_vat_id}
                    onChange={(e) => onChange("billing_vat_id", e.target.value)}
                  />
                </FormField>
              </div>
              <div className="sm:col-span-2">
                <FormField
                  id="billing_address_line1"
                  label="Address line 1"
                  required
                  error={errors.billing_address_line1}
                >
                  <Input
                    id="billing_address_line1"
                    name="billing_address_line1"
                    type="text"
                    placeholder="123 Main Street"
                    defaultValue={values.billing_address_line1}
                    onChange={(e) =>
                      onChange("billing_address_line1", e.target.value)
                    }
                    aria-invalid={!!errors.billing_address_line1}
                    ref={getInputRef("billing_address_line1")}
                  />
                </FormField>
              </div>
              <div className="sm:col-span-2">
                <FormField id="billing_address_line2" label="Address line 2">
                  <Input
                    id="billing_address_line2"
                    name="billing_address_line2"
                    type="text"
                    placeholder="Apt, suite, unit (optional)"
                    defaultValue={values.billing_address_line2}
                    onChange={(e) =>
                      onChange("billing_address_line2", e.target.value)
                    }
                  />
                </FormField>
              </div>
              <FormField
                id="billing_city"
                label="City"
                required
                error={errors.billing_city}
              >
                <Input
                  id="billing_city"
                  name="billing_city"
                  type="text"
                  placeholder="New York"
                  defaultValue={values.billing_city}
                  onChange={(e) => onChange("billing_city", e.target.value)}
                  aria-invalid={!!errors.billing_city}
                  ref={getInputRef("billing_city")}
                />
              </FormField>
              <FormField
                id="billing_postal_code"
                label="Postal code"
                required
                error={errors.billing_postal_code}
              >
                <Input
                  id="billing_postal_code"
                  name="billing_postal_code"
                  type="text"
                  placeholder="10001"
                  defaultValue={values.billing_postal_code}
                  onChange={(e) =>
                    onChange("billing_postal_code", e.target.value)
                  }
                  aria-invalid={!!errors.billing_postal_code}
                  ref={getInputRef("billing_postal_code")}
                />
              </FormField>
              <FormField
                id="billing_country"
                label="Country"
                required
                error={errors.billing_country}
              >
                <CountryPicker
                  name="billing_country"
                  defaultValue={values.billing_country}
                  onChange={(code) => onChange("billing_country", code)}
                />
              </FormField>
              <FormField
                id="billing_phone"
                label="Phone number"
                required
                error={errors.billing_phone}
              >
                <Input
                  id="billing_phone"
                  name="billing_phone"
                  type="tel"
                  placeholder="+1 (555) 123-4567"
                  defaultValue={values.billing_phone}
                  onChange={(e) => onChange("billing_phone", e.target.value)}
                  aria-invalid={!!errors.billing_phone}
                  ref={getInputRef("billing_phone")}
                />
              </FormField>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Save to Profile */}
      {isAuthenticated && (
        <label className="flex cursor-pointer items-center gap-3">
          <Checkbox
            id="save_to_profile"
            checked={values.save_to_profile}
            onCheckedChange={(checked) =>
              onChange("save_to_profile", checked === true)
            }
          />
          <span className="text-sm font-medium text-foreground">
            Save addresses to my profile
          </span>
        </label>
      )}

      {/* Actions */}
      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
        <Button
          variant="outline"
          onClick={onBack}
          data-testid="checkout-back"
          className="gap-2 bg-transparent"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </Button>
        <Button
          data-testid="checkout-submit"
          onClick={onSubmit}
          className="gap-2"
          disabled={isSubmitting}
        >
          {isSubmitting ? "Placing order…" : "Place order"}
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

export function CheckoutForm({
  initialValues,
  onSubmit,
  onBackToCart,
  priceChangePayload,
  isAuthenticated,
}: CheckoutFormProps) {
  const [step, setStep] = React.useState<1 | 2>(1);
  // Once the user advances past step 1 the warning banner is considered
  // acknowledged and must not reappear even if they navigate back.
  const [bannerAcknowledged, setBannerAcknowledged] = React.useState(false);
  const [values, setValues] = React.useState<CheckoutValues>({
    ...defaultValues,
    ...initialValues,
  });
  const [errors, setErrors] = React.useState<FieldErrors>({});
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const firstErrorRef = React.useRef<HTMLInputElement | null>(null);

  const handleChange = (
    field: keyof CheckoutValues,
    value: string | boolean,
  ) => {
    setValues((prev) => ({ ...prev, [field]: value }));
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors((prev) => {
        const updated = { ...prev };
        delete updated[field];
        return updated;
      });
    }
  };

  const validateStep2 = (): boolean => {
    const newErrors: FieldErrors = {};

    // Required fields for step 2
    if (!values.customer_email.trim()) {
      newErrors.customer_email = "Email is required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.customer_email)) {
      newErrors.customer_email = "Please enter a valid email";
    }

    // Shipping required fields
    if (!values.shipping_first_name.trim()) {
      newErrors.shipping_first_name = "First name is required";
    }
    if (!values.shipping_last_name.trim()) {
      newErrors.shipping_last_name = "Last name is required";
    }
    if (!values.shipping_address_line1.trim()) {
      newErrors.shipping_address_line1 = "Address is required";
    }
    if (!values.shipping_city.trim()) {
      newErrors.shipping_city = "City is required";
    }
    if (!values.shipping_postal_code.trim()) {
      newErrors.shipping_postal_code = "Postal code is required";
    }
    if (!values.shipping_country.trim()) {
      newErrors.shipping_country = "Country is required";
    }
    if (!values.shipping_phone.trim()) {
      newErrors.shipping_phone = "Phone number is required";
    }

    // Billing fields (if different from shipping)
    if (!values.billing_same_as_shipping) {
      if (!values.billing_first_name.trim()) {
        newErrors.billing_first_name = "First name is required";
      }
      if (!values.billing_last_name.trim()) {
        newErrors.billing_last_name = "Last name is required";
      }
      if (!values.billing_address_line1.trim()) {
        newErrors.billing_address_line1 = "Address is required";
      }
      if (!values.billing_city.trim()) {
        newErrors.billing_city = "City is required";
      }
      if (!values.billing_postal_code.trim()) {
        newErrors.billing_postal_code = "Postal code is required";
      }
      if (!values.billing_country.trim()) {
        newErrors.billing_country = "Country is required";
      }
      if (!values.billing_phone.trim()) {
        newErrors.billing_phone = "Phone number is required";
      }
    }

    setErrors(newErrors);

    if (Object.keys(newErrors).length > 0) {
      // Focus first error field after render
      setTimeout(() => {
        firstErrorRef.current?.focus();
        firstErrorRef.current?.scrollIntoView({
          behavior: "smooth",
          block: "center",
        });
      }, 0);
      return false;
    }

    return true;
  };

  const handleSubmit = async () => {
    if (validateStep2()) {
      setIsSubmitting(true);
      try {
        await onSubmit(values);
      } finally {
        setIsSubmitting(false);
      }
    }
  };

  return (
    <div className="mx-auto max-w-2xl">
      {/* Stepper Header */}
      <div className="mb-8">
        <StepIndicator currentStep={step} />
      </div>

      {/* Step Content */}
      {step === 1 ? (
        <ShippingPaymentStep
          values={values}
          onChange={handleChange}
          onBack={onBackToCart}
          onContinue={() => {
            setBannerAcknowledged(true);
            setStep(2);
          }}
          priceChangePayload={bannerAcknowledged ? null : priceChangePayload}
        />
      ) : (
        <DetailsStep
          values={values}
          errors={errors}
          onChange={handleChange}
          onBack={() => setStep(1)}
          onSubmit={handleSubmit}
          firstErrorRef={firstErrorRef}
          isAuthenticated={isAuthenticated}
          isSubmitting={isSubmitting}
        />
      )}
    </div>
  );
}
