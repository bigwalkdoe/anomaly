import { type ClassValue, clsx as clsxLib } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsxLib(inputs));
}
