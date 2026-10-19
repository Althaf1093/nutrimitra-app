export type HeightUnit = "cm" | "ft";

const CM_PER_INCH = 2.54;

/** Reads a height typed in cm ("165"), decimal feet ("5.5") or feet and inches (5'6, 5 ft 6 in). Returns cm, or null. */
export function parseHeightCm(text: string, unit: HeightUnit): number | null {
  const value = text.trim().toLowerCase();
  if (!value) return null;
  if (unit === "cm") {
    const cm = Number(value);
    return Number.isFinite(cm) ? cm : null;
  }
  const feetInches = value.match(/^(\d+)\s*(?:'|ft|feet)\s*(\d+(?:\.\d+)?)?\s*(?:"|in|inch|inches)?$/);
  if (feetInches) return (Number(feetInches[1]) * 12 + Number(feetInches[2] || 0)) * CM_PER_INCH;
  const feet = Number(value);
  return Number.isFinite(feet) ? feet * 12 * CM_PER_INCH : null;
}

export function cmToFeetInches(cm: number): { feet: number; inches: number } {
  const totalInches = Math.round(cm / CM_PER_INCH);
  return { feet: Math.floor(totalInches / 12), inches: totalInches % 12 };
}

/** Text to show when switching units, e.g. 167.6 cm -> "5.5" feet. */
export function cmToFeetText(cm: number): string {
  return String(Math.round((cm / CM_PER_INCH / 12) * 100) / 100);
}

export const HEIGHT_MIN_CM = 91;
export const HEIGHT_MAX_CM = 239;
