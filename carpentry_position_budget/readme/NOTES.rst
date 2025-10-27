

to replace for `_get_auto_launch_budget_distribution()`
but no solution to override `_get_total_budgetable_by_analytic()`
in `project.task` and `carpentry.budget.balance`

```
        SELECT
            expense.section_res_model,
            expense.section_id,
            expense.analytic_account_id,
            remaining_per_budget_and_launch.launch_id,
            MIN(
                -- max of auto_reservation is remaining budget
                remaining_per_budget_and_launch.quantity_affected,

                -- else, distribute the expense per budget and launch
                CASE
                    -- project budget
                    WHEN remaining_per_budget_and_launch.launch_id IS NULL OR
                    THEN SUM(expense.amount_expense)
                    
                    -- launch budget
                    ELSE (
                        SUM(expense.amount_expense)
                        * SUM(remaining_per_budget_and_launch.quantity_affected)
                        / SUM(remaining_per_budget.quantity_affected)
                    )
                    END
                END
            ) / (
                -- push budget reservation in h if needed
                CASE
                    WHEN hourly_cost.coef = 0.0
                    THEN 1.0
                    ELSE hourly_cost.coef
            ) AS auto_reservation

        -- `expense` is expense per budget (of the section)
        FROM carpentry_budget_expense AS expense

        LEFT JOIN carpentry_budget_hourly_cost ON hourly_cost
            ON  expense.project_id = hourly_cost.project_id
            AND expense.analytic_account_id = hourly_cost.analytic_account_id

        -- `remaining_per_budget_and_launch` is remaining budget per launch & budget
        LEFT JOIN carpentry_budget_remaining AS remaining_per_budget_and_launch
            ON  remaining_per_budget_and_launch.analytic_account_id = expense.analytic_account_id
            AND remaining_per_budget_and_launch.project_id = expense.project_id

        -- `remaining_per_budget` is remaining budget per analytic
        LEFT JOIN carpentry_budget_remaining AS remaining_per_budget
            ON  remaining_per_budget.analytic_account_id = expense.analytic_account_id
            AND remaining_per_budget.project_id = expense.project_id

        WHERE
            remaining_per_budget_and_launch.expense = %(section_id) AND
            remaining_per_budget_and_launch.expense = %(section_model_id)

        GROUP BY
            expense.section_res_model,
            expense.section_id,
            expense.analytic_account_id,
            remaining_per_budget_and_launch.launch_id

```