"use client";
import { useEffect } from "react";
import clarity from "@microsoft/clarity";

export default function ClaritySnippet() {
  useEffect(() => {
    // Použití proměnné s předponou NEXT_PUBLIC_
    const projectId = process.env.NEXT_PUBLIC_CLARITY_ID;

    if (projectId) {
      clarity.init(projectId);
    }
  }, []);

  return null;
}
