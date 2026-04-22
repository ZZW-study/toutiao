import type { NewsCategory } from "../api/types";

interface CategoryTabsProps {
  activeCategoryId: number;
  categories: NewsCategory[];
  onSelect: (categoryId: number) => void;
}

export function CategoryTabs({
  activeCategoryId,
  categories,
  onSelect,
}: CategoryTabsProps) {
  return (
    <div className="category-tabs">
      {categories.map((category) => (
        <button
          key={category.id}
          type="button"
          className={
            activeCategoryId === category.id
              ? "category-tabs__button is-active"
              : "category-tabs__button"
          }
          onClick={() => onSelect(category.id)}
        >
          {category.name}
        </button>
      ))}
    </div>
  );
}
