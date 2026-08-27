import type { MissionDraft } from "../state/mission";

export type WizardStep = "/" | "/payload" | "/payload/summary" | "/roi" | "/parameters" | "/result";

export function firstMissingStep(draft: MissionDraft): WizardStep | null {
  if (!draft.family) return "/";
  if (!draft.payload) return "/payload";
  if (!draft.roi) return "/roi";
  if (!draft.parameters) return "/parameters";
  return null;
}

