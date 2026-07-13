import type { SnapshotItem, TaxonomyOption, TaxonomyOptions } from "../services/contracts";
import type { TaxonomyFilterSelection } from "./filtering";

export type AvailableTaxonomyOptions = TaxonomyOptions;

export function buildAvailableTaxonomyOptions(
  items: SnapshotItem[],
  taxonomy: TaxonomyOptions,
  selection: TaxonomyFilterSelection,
): AvailableTaxonomyOptions {
  const primaryCodes = new Set(items.map((item) => item.primary_category));
  const primaryItems = selection.primaryCategories.length
    ? items.filter((item) => selection.primaryCategories.includes(item.primary_category))
    : items;
  const secondaryCodes = new Set(
    primaryItems.map((item) => item.secondary_category).filter((value): value is string => Boolean(value)),
  );
  const secondaryItems = selection.secondaryCategories.length
    ? primaryItems.filter(
        (item) => item.secondary_category && selection.secondaryCategories.includes(item.secondary_category),
      )
    : primaryItems;
  const tertiaryCodes = new Set(secondaryItems.flatMap((item) => item.tertiary_categories));
  const regionCodes = new Set(items.flatMap((item) => item.regions));

  return {
    primary_categories: taxonomy.primary_categories.filter((option) => primaryCodes.has(option.code)),
    secondary_categories: taxonomy.secondary_categories.filter(
      (option) =>
        secondaryCodes.has(option.code) &&
        (!selection.primaryCategories.length || option.parent_codes.some((code) => selection.primaryCategories.includes(code))),
    ),
    tertiary_categories: taxonomy.tertiary_categories.filter(
      (option) =>
        tertiaryCodes.has(option.code) &&
        (!selection.secondaryCategories.length ||
          !option.parent_codes.length ||
          option.parent_codes.some((code) => selection.secondaryCategories.includes(code))),
    ),
    regions: taxonomy.regions.filter((option) => regionCodes.has(option.code)),
  };
}

export function taxonomyOptionLabel(option: TaxonomyOption) {
  return option.label_en === option.label_zh ? option.label_en : `${option.label_zh} ${option.label_en}`;
}

export function pruneSelection(values: string[], options: TaxonomyOption[]) {
  const available = new Set(options.map((option) => option.code));
  return values.filter((value) => available.has(value));
}
