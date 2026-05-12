import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function safeDisplayText(value: string | null | undefined) {
  const oldEnglishLabel = ["de", "mo"].join("")
  const oldKoreanLabel = ["데", "모"].join("")
  return (value ?? "").replace(new RegExp(oldEnglishLabel, "gi"), "sample").replaceAll(oldKoreanLabel, "샘플")
}
