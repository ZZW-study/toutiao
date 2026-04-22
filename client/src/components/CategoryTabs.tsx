import { useEffect, useState } from "react";

import type { NewsCategory } from "../api/types";

interface CategoryTabsProps {
  categories: NewsCategory[];
  activeCategoryId: number;
  onSelect: (categoryId: number) => void;
}

export function CategoryTabs({
  categories,
  activeCategoryId,
  onSelect,
}: CategoryTabsProps) {
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };

    onScroll();
    window.addEventListener("scroll", onScroll, {
      passive: true,
    });

    return () => {
      window.removeEventListener("scroll", onScroll);
    };
  }, []);

  return (
    <section
      className={
        isScrolled
          ? "category-tabs is-scrolled"
          : "category-tabs"
      }
      aria-label="新闻分类"
    >
      <div className="category-tabs__inner">
        {categories.map((category) => (
          <button
            key={category.id}
            type="button"
            className={
              category.id === activeCategoryId
                ? "category-tabs__button is-active"
                : "category-tabs__button"
            }
            onClick={() => onSelect(category.id)}
          >
            {category.name}
          </button>
        ))}
      </div>
    </section>
  );
}
