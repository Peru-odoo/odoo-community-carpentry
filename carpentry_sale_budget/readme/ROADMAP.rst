
#===== Carpentry Planning =====#
def get_planning_dashboard_data(self):
    return super().get_planning_dashboard_data() | self._get_planning_dashboard_cost_data()

def _get_planning_dashboard_cost_data(self):
    return {}
    # {
    #     'market_reviewed': self.market_reviewed,
    #     'budget_total': self.budget_total,
    #     'budget_progress': round(self.budget_progress),
    # }
