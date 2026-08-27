import worldCountries from "../../data/world-countries.geo.json";
import { featureCentroid } from "./countryCentroids";

export type CountryFeatureProperties = {
  name?: string;
  ADMIN?: string;
  NAME?: string;
  ISO_A3?: string;
  iso_a3?: string;
};

type Position = [number, number]; // [lon, lat]

type CountryGeometry =
  | {
      type: "Polygon";
      coordinates: Position[][];
    }
  | {
      type: "MultiPolygon";
      coordinates: Position[][][];
    };

type CountryFeature = {
  type: "Feature";
  properties: CountryFeatureProperties;
  geometry: CountryGeometry;
};

type CountryFeatureCollection = {
  type: "FeatureCollection";
  features: CountryFeature[];
};

function asCountryCollection(data: unknown): CountryFeatureCollection {
  return data as CountryFeatureCollection;
}

export function getCountryName(props: CountryFeatureProperties): string {
  return props.name ?? props.ADMIN ?? props.NAME ?? props.ISO_A3 ?? props.iso_a3 ?? "";
}

export function getCountryCode(props: CountryFeatureProperties): string {
  return props.ISO_A3 ?? props.iso_a3 ?? "";
}

export function normalizeCountryQuery(query: string): string {
  return query.trim().toLowerCase();
}

export function matchesCountryQuery(props: CountryFeatureProperties, query: string): boolean {
  const q = normalizeCountryQuery(query);
  if (!q) return false;

  const name = getCountryName(props).toLowerCase();
  const code = getCountryCode(props).toLowerCase();

  return name === q || name.includes(q) || code === q;
}

export type ResolvedCountry = {
  id: string; // ISO_A3
  name: string;
  lat: number;
  lon: number;
};

export function resolveCountry(query: string): ResolvedCountry | null {
  const q = normalizeCountryQuery(query);
  if (!q) return null;

  const fc = asCountryCollection(worldCountries);
  const feature = fc.features.find((f) => matchesCountryQuery(f.properties, q));
  if (!feature) return null;

  const [lon, lat] = featureCentroid(feature.geometry);
  const id = getCountryCode(feature.properties);
  const name = getCountryName(feature.properties);
  if (!id || !name) return null;

  return { id, name, lat, lon };
}

export function getCountryFeatureByIso3(iso3: string): CountryFeature | null {
  const code = normalizeCountryQuery(iso3).toUpperCase();
  if (!code) return null;
  const fc = asCountryCollection(worldCountries);
  return fc.features.find((f) => getCountryCode(f.properties).toUpperCase() === code) ?? null;
}

