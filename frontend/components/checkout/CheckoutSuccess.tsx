import { CheckCircle, Mail, Info } from "lucide-react";

import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

interface CheckoutSuccessProps {
  customerEmail?: string;
  onContinueShopping: () => void;
}

export function CheckoutSuccess({
  customerEmail,
  onContinueShopping,
}: CheckoutSuccessProps) {
  return (
    <div
      data-testid="guest-checkout-success"
      className="mx-auto flex w-full max-w-lg items-center justify-center py-8 md:py-16"
    >
      <Card className="w-full shadow-lg">
        {/* Top Section - Success */}
        <CardHeader className="items-center gap-4 pb-4 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
            <CheckCircle className="h-9 w-9" aria-hidden="true" />
          </div>
          <div className="flex flex-col gap-2">
            <h1 className="text-2xl font-bold text-foreground text-balance">
              Order Created Successfully
            </h1>
            <p className="text-muted-foreground leading-relaxed">
              {"We've sent an order access link to your email."}
            </p>
            {customerEmail && (
              <p className="inline-flex items-center justify-center gap-1.5 text-sm font-medium text-foreground">
                <Mail
                  className="h-4 w-4 text-muted-foreground"
                  aria-hidden="true"
                />
                {"Email sent to: "}
                <span className="font-semibold">{customerEmail}</span>
              </p>
            )}
          </div>
        </CardHeader>

        <Separator />

        {/* Middle Section - Info Box */}
        <CardContent className="px-6 py-6">
          <div className="rounded-lg border border-border bg-muted/60 p-4">
            <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-foreground">
              <Info
                className="h-4 w-4 text-muted-foreground"
                aria-hidden="true"
              />
              Guest Checkout Info
            </div>
            <ul className="flex flex-col gap-1.5 pl-6 text-sm text-muted-foreground leading-relaxed">
              <li className="list-disc">
                This order was placed as a guest checkout.
              </li>
              <li className="list-disc">
                The order access link in your email is required to view order
                details.
              </li>
              <li className="list-disc">
                {"If you don't see the email, please check your spam folder."}
              </li>
            </ul>
          </div>

          {/* Demo Note */}
          <p className="mt-4 text-center text-xs text-muted-foreground">
            Shipping and payment are simulated in this demo.
          </p>
        </CardContent>

        <Separator />

        {/* Bottom Section - CTA */}
        <CardFooter className="justify-center px-6 py-6">
          <Button
            size="lg"
            className="w-full sm:w-auto sm:min-w-50"
            onClick={onContinueShopping}
          >
            Continue Shopping
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
