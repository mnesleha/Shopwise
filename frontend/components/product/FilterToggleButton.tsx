"use client"

import { SlidersHorizontal } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface FilterToggleButtonProps {
  isOpen: boolean
  onToggle: () => void
}

export function FilterToggleButton({ isOpen, onToggle }: FilterToggleButtonProps) {
  return (
    <Button
      variant={isOpen ? "default" : "outline"}
      size="icon"
      onPointerDown={(e) => {
        // On mobile touch devices the browser automatically releases pointer
        // capture on pointerup. Radix UI's internal cleanup then tries to call
        // releasePointerCapture() again on the already-released pointer, throwing
        // "No active pointer with the given id is found". Releasing capture
        // proactively here prevents Radix from needing to do it in cleanup.
        e.currentTarget.releasePointerCapture(e.pointerId);
      }}
      onClick={onToggle}
      aria-label={isOpen ? "Close filters" : "Open filters"}
      aria-expanded={isOpen}
      className={cn(
        "relative transition-colors",
        isOpen && "ring-2 ring-ring/30"
      )}
    >
      <SlidersHorizontal
        className={cn(
          "size-4 transition-transform duration-200",
          isOpen && "rotate-90"
        )}
      />
    </Button>
  )
}
