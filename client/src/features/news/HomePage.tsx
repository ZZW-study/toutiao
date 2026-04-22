import { startTransition, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";

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
  const leadStory = newsList[0] ?? null;
  const streamItems = leadStory ? newsList.slice(1) : newsList;

  const updateCategory = (categoryId: number) => {
    const nextSearchParams = new URLSearchParams(searchParams);
    nextSearchParams.set("category", String(categoryId));
    nextSearchParams.set("page", "1");
    startTransition(() => {
      setSearchParams(nextSearchParams);
    });
  };

  const updatePage = (nextPage: number) => {
    const nextSearchParams = new URLSearchParams(searchParams);
    nextSearchParams.set("page", String(nextPage));
    startTransition(() => {
      setSearchParams(nextSearchParams);
    });
  };

  return (
    <div className="page page--home">
      <section className="hero-panel">
        <div className="hero-panel__copy">
          <p className="eyebrow">Headline Stream</p>
          <h1>今日要闻，一眼扫清主线。</h1>
          <p>
            用频道切换组织信息流，用详情页完成深度阅读，用 AI
            问答快速压缩信息密度。
          </p>
          <div className="hero-panel__actions">
            <Link to="/ask" className="button button--primary">
              去问 AI
            </Link>
            <span className="hero-panel__meta">
              当前频道：{activeCategory?.name ?? "加载中"}
            </span>
          </div>
        </div>

        <div className="hero-panel__stats">
          <div>
            <strong>{categories.length}</strong>
            <span>频道数量</span>
          </div>
          <div>
            <strong>{newsQuery.data?.total ?? 0}</strong>
            <span>当前频道内容数</span>
          </div>
        </div>
      </section>

      {categoriesQuery.isLoading ? (
        <LoadingBlock label="正在加载频道..." />
      ) : categoriesQuery.isError ? (
        <ErrorNotice
          title="频道加载失败"
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
          <div className="home-grid__lead">
            {newsQuery.isLoading ? (
              <LoadingBlock label="正在整理头条焦点..." />
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
              <EmptyState
                title="当前频道暂无头条"
                description="换一个频道试试，或者稍后再回来刷新。"
              />
            )}
          </div>

          <div className="stream-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">News Feed</p>
                <h2>{activeCategory.name}</h2>
              </div>
              <span>{newsQuery.data?.total ?? 0} 条</span>
            </div>

            {newsQuery.isLoading ? (
              <LoadingBlock label="正在加载新闻流..." />
            ) : newsQuery.isError ? (
              <ErrorNotice
                title="新闻流加载失败"
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
            ) : (
              <EmptyState
                title="这一页没有更多内容"
                description="可以翻到下一页，或者切换到其他频道继续浏览。"
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
