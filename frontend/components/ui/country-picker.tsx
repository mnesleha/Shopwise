"use client";

import * as React from "react";
import { Check, ChevronsUpDown } from "lucide-react";
import countryList from "react-select-country-list";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

// Memoised at module level — the list never changes at runtime.
const OPTIONS = countryList().getData();

/** Map an ISO 3166-1 alpha-2 country code to its English display name. */
export function getCountryName(code: string): string {
  return OPTIONS.find((o) => o.value === code)?.label ?? code;
}

interface CountryPickerProps {
  id?: string;
  /** Hidden input name — used by FormData on submit. */
  name: string;
  defaultValue?: string;
  ariaInvalid?: boolean;
  buttonRef?: React.Ref<HTMLButtonElement>;
  /**
   * Called with the ISO 3166-1 alpha-2 code whenever the selection changes.
   * Use this for controlled-state forms (e.g. CheckoutForm) where the parent
   * tracks values explicitly rather than reading them from FormData.
   */
  onChange?: (value: string) => void;
}

/**
 * Searchable country combobox backed by a hidden `<input>` so that
 * `new FormData(form)` picks up the ISO code without any controlled state in
 * the parent — consistent with the ADR-034 pattern used across all address forms.
 */
export function CountryPicker({
  id,
  name,
  defaultValue = "",
  ariaInvalid = false,
  buttonRef,
  onChange,
}: CountryPickerProps) {
  const [open, setOpen] = React.useState(false);
  const [value, setValue] = React.useState(defaultValue);

  const handleSelect = (code: string) => {
    setValue(code);
    onChange?.(code);
    setOpen(false);
  };

  return (
    <>
      {/* Hidden input ensures FormData on the parent form captures the ISO code. */}
      <input type="hidden" name={name} value={value} />

      <Popover open={open} onOpenChange={setOpen} modal={true}>
        <PopoverTrigger asChild>
          <Button
            ref={buttonRef}
            id={id}
            variant="outline"
            role="combobox"
            aria-expanded={open}
            aria-invalid={ariaInvalid}
            className={cn(
              "w-full justify-between",
              ariaInvalid &&
                "border-destructive bg-destructive/5 text-foreground focus-visible:border-destructive focus-visible:ring-destructive/20 dark:focus-visible:ring-destructive/40",
            )}
          >
            {value
              ? OPTIONS.find((opt) => opt.value === value)?.label
              : "Select country…"}
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[--radix-popover-trigger-width] p-0">
          <Command>
            <CommandInput placeholder="Search country…" />
            <CommandEmpty>No country found.</CommandEmpty>
            <CommandGroup className="max-h-60 overflow-y-auto">
              {OPTIONS.map((option) => (
                <CommandItem
                  key={option.value}
                  value={option.label}
                  onSelect={() => handleSelect(option.value)}
                >
                  <Check
                    className={cn(
                      "mr-2 h-4 w-4",
                      value === option.value ? "opacity-100" : "opacity-0",
                    )}
                  />
                  {option.label}
                </CommandItem>
              ))}
            </CommandGroup>
          </Command>
        </PopoverContent>
      </Popover>
    </>
  );
}
