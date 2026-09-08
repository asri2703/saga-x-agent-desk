-- ============================================================
-- 008 — Spend precision
-- ============================================================
-- `usage_this_month` rounded to 2 decimals while `agent_runs.cost_usd`
-- keeps 6. On the activity screen that showed $0.11 next to $0.1135 —
-- the same money, two numbers. Small, but a figures screen that appears
-- to contradict itself is a figures screen nobody trusts.
--
-- Also matters at the edge: rounding down slightly under-counts the
-- spend the monthly cap is checked against.
-- ============================================================

-- `create or replace view` cannot change a column's type, so the view
-- has to go first. Nothing depends on it but application code.
drop view if exists desk.usage_this_month;

create view desk.usage_this_month as
  select coalesce(sum(cost_usd), 0)::numeric(12,6) as spent_usd,
         count(*)                                  as calls
    from desk.usage
   where created_at >= date_trunc('month', now());
