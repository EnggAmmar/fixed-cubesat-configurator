import type { Feature, FeatureCollection, Geometry } from "geojson";
import worldCountries from "../../data/world-countries.geo.json";
import { COUNTRY_ALIASES } from "./countryAliases";
import { featureCentroid } from "./countryCentroids";

type CountryFeatureProperties = {
  name?: string;
  ADMIN?: string;
  NAME?: string;
  ISO_A3?: string;
  iso_a3?: string;
};

type CountryFeature = Feature<Geometry, CountryFeatureProperties | null>;

export type ResolvedCountry = {
  id: string;
  name: string;
  lat: number;
  lon: number;
};

function normalize(value: string) {
  return value.trim().toLowerCase();
}

function getName(props: CountryFeatureProperties | null | undefined): string {
  return props?.name ?? props?.ADMIN ?? props?.NAME ?? "";
}

function getCode(props: CountryFeatureProperties | null | undefined): string {
  return props?.ISO_A3 ?? props?.iso_a3 ?? "";
}

export function resolveCountry(query: string): ResolvedCountry | null {
  const q = normalize(query);
  if (!q) return null;

  const collection = worldCountries as unknown as FeatureCollection<
    Geometry,
    CountryFeatureProperties | null
  >;
  const features: CountryFeature[] = collection.features ?? [];

  const aliasCode = COUNTRY_ALIASES[q];
  if (aliasCode) {
    const feature = features.find((f) => getCode(f.properties) === aliasCode);
    if (feature) {
      const [lon, lat] = featureCentroid(feature.geometry);
      return {
        id: getCode(feature.properties),
        name: getName(feature.properties),
        lat,
        lon,
      };
    }
  }

  const exact = features.find((f) => normalize(getName(f.properties)) === q);
  if (exact) {
    const [lon, lat] = featureCentroid(exact.geometry);
    return {
      id: getCode(exact.properties),
      name: getName(exact.properties),
      lat,
      lon,
    };
  }

  const partial = features.find((f) => normalize(getName(f.properties)).includes(q));
  if (partial) {
    const [lon, lat] = featureCentroid(partial.geometry);
    return {
      id: getCode(partial.properties),
      name: getName(partial.properties),
      lat,
      lon,
    };
  }

  return null;
}

