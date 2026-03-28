"use client";

import {
  CircleCheckIcon,
  InfoIcon,
  Loader2Icon,
  OctagonXIcon,
  TriangleAlertIcon,
} from "lucide-react";
import { useTheme } from "next-themes";
import { Toaster as Sonner, type ToasterProps } from "sonner";

const toastActionButtonStyle: React.CSSProperties = {
  background: "var(--background)",
  color: "var(--foreground)",
  border: "1px solid var(--border)",
  borderRadius: "calc(var(--radius) - 2px)",
  boxShadow: "none",
};

const Toaster = ({ ...props }: ToasterProps) => {
  const { theme = "system" } = useTheme();

  return (
    <Sonner
      theme={theme as ToasterProps["theme"]}
      className="toaster group"
      toastOptions={{
        actionButtonStyle: toastActionButtonStyle,
        cancelButtonStyle: toastActionButtonStyle,
        classNames: {
          actionButton:
            "rounded-md border border-border bg-background text-foreground shadow-none transition-colors hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
          cancelButton:
            "rounded-md border border-border bg-background text-foreground shadow-none transition-colors hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
          closeButton:
            "border-border bg-background/90 text-muted-foreground shadow-none transition-colors hover:bg-background hover:text-foreground",
        },
      }}
      icons={{
        success: <CircleCheckIcon className="size-4" />,
        info: <InfoIcon className="size-4" />,
        warning: <TriangleAlertIcon className="size-4" />,
        error: <OctagonXIcon className="size-4" />,
        loading: <Loader2Icon className="size-4 animate-spin" />,
      }}
      style={
        {
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--border)",
          "--border-radius": "var(--radius)",
        } as React.CSSProperties
      }
      {...props}
    />
  );
};

export { Toaster };
