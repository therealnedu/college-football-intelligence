import type { DataMode } from "@/lib/types";

export function provenanceTitle(dataMode: DataMode): string {
  if (dataMode === "fixture") {
    return "Fixture data. Not real college football statistics.";
  }
  return "Live data from CollegeFootballData.com. Not official NCAA, conference, or school statistics.";
}

export function deliveryDetail(delivery: "api" | "snapshot", generatedAt: string | null): string {
  if (delivery === "snapshot") {
    const when = generatedAt ? ` Built ${generatedAt}.` : "";
    return `This page is a static snapshot. Opening it does not call the data provider.${when}`;
  }
  return "This page reads the CFIP API. The provider key stays on the server.";
}
