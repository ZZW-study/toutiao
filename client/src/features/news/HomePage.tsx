import { Link, useSearchParams } from "react-router-dom";
import { useEffect } from "react";

import { getErrorMessage } from "../../api/errors";
import { CategoryTabs } from "../../components/CategoryTabs";
import { EmptyState } from "../../components/EmptyState";
import { ErrorNotice } from "../../components/ErrorNotice";
import { LeadStory } from "../../components/LeadStory";
import { LoadingBlock } from "../../components/LoadingBlock";
import { NewsFeedItem } from "../../components/NewsFeedItem";
import { Pagination } from "../../components/Pagination";
import { useCategories, useNewsList } from "./hooks";

function parsePositiveNumber(value: string | null, fallback: number) {
  const parsedValue = Number(value);
  return Number.isInteger(parsedValue) && parsedValue > 0
    ? parsedValue
    : fallback;
}

export function HomePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const categoriesQuery = useCategories();
  const categories = categoriesQuery.data ?? [];

  const page = parsePositiveNumber(searchParams.get("page"), 1);
  const requestedCategoryId = parsePositiveNumber(
    searchParams.get("category"),
    0,
  );
  const activeCategory = categories.find(
    (category) => category.id === requestedCategoryId,
  );

  useEffect(() => {
    if (!categories.length || activeCategory) {
      return;
    }

    const nextSearchParams = new URLSearchParams(searchParams);
    nextSearchParams.set("category", String(categories[0].id));
    nextSearchParams.set("page", "1");
    setSearchParams(nextSearchParams, { replace: true });
  }, [
    activeCategory,
    categories,
    searchParams,
    setSearchParams,
  ]);

  const newsQuery = useNewsList(
    activeCategory?.id ?? 0,
    page,
    Boolean(activeCategory),
  );
  const newsList = newsQuery.data?.list ?? [];
  const leadStory = page === 1 ? newsList[0] ?? null : null;
  const streamItems =
    page === 1 && leadStory ? newsList.slice(1) : newsList;

  const updateCategory = (categoryId: number) => {
    const nextSearchParams = new URLSearchParams(searchParams);
    nextSearchParams.set("category", String(categoryId));
    nextSearchParams.set("page", "1");
    setSearchParams(nextSearchParams);
  };

  const updatePage = (nextPage: number) => {
    const nextSearchParams = new URLSearchParams(searchParams);
    nextSearchParams.set("page", String(nextPage));
    setSearchParams(nextSearchParams);
  };

  return (
    <div className="page page--home">
      <section className="home-intro reveal">
        <div className="home-intro__copy">
          <p className="eyebrow">Today&apos;s Desk</p>
          <h1>头条编辑台</h1>
          <p className="home-intro__description">
            用桌面视图查看新闻主线，先抓住重点，再进入完整报道。
          </p>
        </div>

        <aside className="home-intro__aside">
          <span>Current Section</span>
          <strong>{activeCategory?.name ?? "等待分类"}</strong>
          <Link to="/ask" className="text-action">
            进入 AI 问答
          </Link>
        </aside>
      </section>

      {categoriesQuery.isLoading ? (
        <LoadingBlock label="正在加载栏目..." />
      ) : categoriesQuery.isError ? (
        <ErrorNotice
          title="栏目加载失败"
          message={getErrorMessage(categoriesQuery.error)}
          onRetry={() => {
            void categoriesQuery.refetch();
          }}
        />
      ) : (
        <CategoryTabs
          categories={categories}
          activeCategoryId={activeCategory?.id ?? 0}
          onSelect={updateCategory}
        />
      )}

      {activeCategory ? (
        <section className="home-grid">
          <div className="home-grid__lead reveal">
            {newsQuery.isLoading ? (
              <LoadingBlock label="正在整理焦点新闻..." />
            ) : newsQuery.isError ? (
              <ErrorNotice
                title="新闻列表加载失败"
                message={getErrorMessage(newsQuery.error)}
                onRetry={() => {
                  void newsQuery.refetch();
                }}
              />
            ) : leadStory ? (
              <LeadStory item={leadStory} />
            ) : (
              <div className="section-sheet">
                <p className="eyebrow">Section Brief</p>
                <h2>{activeCategory.name}</h2>
                <p>
                  第 {page} 页当前没有焦点位，右侧保留列表流继续阅读。
                </p>
              </div>
            )}
          </div>

          <div className="home-grid__stream">
            <header className="stream-head">
              <div>
                <p className="eyebrow">News Stream</p>
                <h2>{activeCategory.name}</h2>
              </div>
              <span>
                {newsQuery.data?.total ?? 0} 条内容
              </span>
            </header>

            {newsQuery.isLoading ? (
              <LoadingBlock label="正在加载新闻列表..." />
            ) : newsQuery.isError ? (
              <ErrorNotice
                title="新闻列表加载失败"
                message={getErrorMessage(newsQuery.error)}
                onRetry={() => {
                  void newsQuery.refetch();
                }}
              />
            ) : streamItems.length ? (
              <div className="news-stream">
                {streamItems.map((item) => (
                  <NewsFeedItem key={item.id} item={item} />
                ))}
              </div>
            ) : newsList.length ? (
              <EmptyState
                title="本页只有焦点文章"
                description="可以翻到下一页，或切换到其他栏目继续浏览。"
              />
            ) : (
              <EmptyState
                title="当前栏目还没有内容"
                description="稍后再看，或切换到其他栏目。"
              />
            )}

            <Pagination
              page={page}
              total={newsQuery.data?.total ?? 0}
              hasMore={newsQuery.data?.hasMore ?? false}
              onPageChange={updatePage}
            />
          </div>
        </section>
      ) : null}
    </div>
  );
}
