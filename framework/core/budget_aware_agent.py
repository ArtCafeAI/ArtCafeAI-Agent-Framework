"""
Budget-Aware Agent - Agent with cost tracking and budget constraints.

Implements cost controls to prevent runaway spending in autonomous agents,
following Anthropic's warning about higher costs with autonomous agents.
"""

import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from .verified_agent import VerifiedAgent


class CostUnit(Enum):
    """Units for tracking costs."""
    TOKENS = "tokens"
    REQUESTS = "requests"
    DOLLARS = "dollars"
    CREDITS = "credits"


@dataclass
class CostEntry:
    """A single cost entry."""
    amount: float
    unit: CostUnit
    operation: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class Budget:
    """Budget configuration."""
    limit: float
    unit: CostUnit
    period: timedelta
    strict: bool = True  # If True, hard stop when budget exceeded
    warning_threshold: float = 0.8  # Warn at 80% of budget


class BudgetExceededException(Exception):
    """Raised when budget is exceeded and strict mode is enabled."""
    pass


class CostTracker:
    """Tracks costs and enforces budgets."""
    
    def __init__(self):
        self.entries: List[CostEntry] = []
        self.budgets: List[Budget] = []
        self.total_by_unit: Dict[CostUnit, float] = {unit: 0.0 for unit in CostUnit}
        
    def add_budget(self, budget: Budget):
        """Add a budget constraint."""
        self.budgets.append(budget)
    
    def record(
        self,
        amount: float,
        unit: CostUnit,
        operation: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CostEntry:
        """Record a cost entry."""
        entry = CostEntry(
            amount=amount,
            unit=unit,
            operation=operation,
            metadata=metadata
        )
        self.entries.append(entry)
        self.total_by_unit[unit] += amount
        return entry
    
    def get_usage_in_period(
        self,
        unit: CostUnit,
        period: timedelta,
        as_of: Optional[datetime] = None
    ) -> float:
        """Get total usage for a unit within a time period."""
        if as_of is None:
            as_of = datetime.utcnow()
        
        cutoff = as_of - period
        total = sum(
            entry.amount
            for entry in self.entries
            if entry.unit == unit and entry.timestamp >= cutoff
        )
        return total
    
    def check_budgets(self) -> List[Dict[str, Any]]:
        """Check all budgets and return status."""
        results = []
        now = datetime.utcnow()
        
        for budget in self.budgets:
            usage = self.get_usage_in_period(budget.unit, budget.period, now)
            percentage = (usage / budget.limit) * 100 if budget.limit > 0 else 0
            
            status = {
                "budget": budget,
                "usage": usage,
                "limit": budget.limit,
                "percentage": percentage,
                "exceeded": usage >= budget.limit,
                "warning": percentage >= (budget.warning_threshold * 100),
                "remaining": max(0, budget.limit - usage)
            }
            results.append(status)
            
            if status["exceeded"] and budget.strict:
                raise BudgetExceededException(
                    f"Budget exceeded: {usage:.2f}/{budget.limit:.2f} {budget.unit.value} "
                    f"in {budget.period.days} days"
                )
        
        return results
    
    def can_proceed(self, estimated_cost: float, unit: CostUnit) -> bool:
        """Check if an operation can proceed within budget constraints."""
        for budget in self.budgets:
            if budget.unit == unit:
                usage = self.get_usage_in_period(budget.unit, budget.period)
                if usage + estimated_cost > budget.limit:
                    return False
        return True
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of costs and budgets."""
        return {
            "total_entries": len(self.entries),
            "totals_by_unit": dict(self.total_by_unit),
            "budget_status": self.check_budgets(),
            "recent_entries": [
                {
                    "amount": e.amount,
                    "unit": e.unit.value,
                    "operation": e.operation,
                    "timestamp": e.timestamp.isoformat()
                }
                for e in self.entries[-10:]  # Last 10 entries
            ]
        }


class BudgetAwareAgent(VerifiedAgent):
    """
    An agent that tracks costs and enforces budget constraints.
    
    Example:
        ```python
        agent = BudgetAwareAgent(
            daily_dollar_budget=10.0,
            hourly_request_budget=1000
        )
        
        # Costs are automatically tracked for LLM calls
        response = await agent.call_llm("Generate a story")
        
        # Check budget status
        status = agent.get_budget_status()
        ```
    """
    
    def __init__(
        self,
        agent_id: str = None,
        agent_type: str = "budget_aware",
        daily_dollar_budget: Optional[float] = None,
        hourly_request_budget: Optional[int] = None,
        monthly_token_budget: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize a budget-aware agent.
        
        Args:
            agent_id: Agent identifier
            agent_type: Type of agent
            daily_dollar_budget: Daily spending limit in dollars
            hourly_request_budget: Hourly request limit
            monthly_token_budget: Monthly token limit
            **kwargs: Additional configuration
        """
        super().__init__(agent_id=agent_id, agent_type=agent_type, **kwargs)
        
        self.cost_tracker = CostTracker()
        
        # Set up default budgets
        if daily_dollar_budget:
            self.cost_tracker.add_budget(Budget(
                limit=daily_dollar_budget,
                unit=CostUnit.DOLLARS,
                period=timedelta(days=1),
                strict=kwargs.get("strict_dollar_budget", True)
            ))
        
        if hourly_request_budget:
            self.cost_tracker.add_budget(Budget(
                limit=float(hourly_request_budget),
                unit=CostUnit.REQUESTS,
                period=timedelta(hours=1),
                strict=kwargs.get("strict_request_budget", False)
            ))
        
        if monthly_token_budget:
            self.cost_tracker.add_budget(Budget(
                limit=float(monthly_token_budget),
                unit=CostUnit.TOKENS,
                period=timedelta(days=30),
                strict=kwargs.get("strict_token_budget", False)
            ))
        
        # Cost estimation models (can be overridden)
        self.token_cost_per_1k = kwargs.get("token_cost_per_1k", {
            "gpt-4": 0.03,
            "gpt-3.5-turbo": 0.002,
            "claude-3-opus": 0.015,
            "claude-3-sonnet": 0.003,
            "claude-3-haiku": 0.00025
        })
        
        # Circuit breaker for error scenarios
        self.error_threshold = kwargs.get("error_threshold", 5)
        self.error_window = kwargs.get("error_window", 300)  # 5 minutes
        self.recent_errors = []
        
        self.add_capability("cost_tracking")
        self.add_capability("budget_enforcement")
    
    async def call_llm(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Call LLM with cost tracking and budget enforcement.
        
        Args:
            prompt: The prompt to send
            model: Optional model override
            max_tokens: Maximum tokens to generate
            **kwargs: Additional LLM parameters
            
        Returns:
            LLM response with cost information
            
        Raises:
            BudgetExceededException: If budget would be exceeded
        """
        # Estimate cost
        estimated_tokens = len(prompt.split()) * 1.3 + (max_tokens or 500)
        estimated_cost = self._estimate_cost(estimated_tokens, model)
        
        # Check budgets
        if not self.cost_tracker.can_proceed(1, CostUnit.REQUESTS):
            raise BudgetExceededException("Request budget exceeded")
        
        if not self.cost_tracker.can_proceed(estimated_tokens, CostUnit.TOKENS):
            raise BudgetExceededException("Token budget exceeded")
        
        if not self.cost_tracker.can_proceed(estimated_cost, CostUnit.DOLLARS):
            raise BudgetExceededException("Dollar budget exceeded")
        
        # Check circuit breaker
        self._check_circuit_breaker()
        
        # Record the request
        self.cost_tracker.record(1, CostUnit.REQUESTS, "llm_call", {
            "model": model,
            "prompt_preview": prompt[:100]
        })
        
        try:
            # Make the actual LLM call
            response = await self._llm_call_impl(prompt, model, max_tokens, **kwargs)
            
            # Record actual costs
            actual_tokens = response.get("usage", {}).get("total_tokens", estimated_tokens)
            actual_cost = self._calculate_cost(actual_tokens, model)
            
            self.cost_tracker.record(actual_tokens, CostUnit.TOKENS, "llm_call", {
                "model": model,
                "prompt_tokens": response.get("usage", {}).get("prompt_tokens"),
                "completion_tokens": response.get("usage", {}).get("completion_tokens")
            })
            
            self.cost_tracker.record(actual_cost, CostUnit.DOLLARS, "llm_call", {
                "model": model,
                "tokens": actual_tokens
            })
            
            # Add cost info to response
            response["cost_info"] = {
                "tokens": actual_tokens,
                "cost_dollars": actual_cost,
                "budget_remaining": self._get_remaining_budget()
            }
            
            return response
            
        except Exception as e:
            # Record error
            self._record_error(str(e))
            raise
    
    async def _llm_call_impl(
        self,
        prompt: str,
        model: Optional[str],
        max_tokens: Optional[int],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Actual LLM call implementation. Override in subclasses.
        """
        # This would be implemented with actual LLM provider
        # For now, return a mock response
        return {
            "content": "Mock LLM response",
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": 50,
                "total_tokens": len(prompt.split()) + 50
            }
        }
    
    def _estimate_cost(self, tokens: float, model: Optional[str]) -> float:
        """Estimate cost in dollars for a number of tokens."""
        model = model or "gpt-3.5-turbo"
        rate = self.token_cost_per_1k.get(model, 0.002)
        return (tokens / 1000) * rate
    
    def _calculate_cost(self, tokens: int, model: Optional[str]) -> float:
        """Calculate actual cost in dollars."""
        return self._estimate_cost(float(tokens), model)
    
    def _get_remaining_budget(self) -> Dict[str, float]:
        """Get remaining budget for each unit."""
        remaining = {}
        for status in self.cost_tracker.check_budgets():
            unit = status["budget"].unit.value
            remaining[f"{unit}_remaining"] = status["remaining"]
            remaining[f"{unit}_percentage_used"] = status["percentage"]
        return remaining
    
    def _check_circuit_breaker(self):
        """Check if too many errors have occurred recently."""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.error_window)
        
        # Clean old errors
        self.recent_errors = [
            error_time for error_time in self.recent_errors
            if error_time > cutoff
        ]
        
        if len(self.recent_errors) >= self.error_threshold:
            raise Exception(
                f"Circuit breaker tripped: {len(self.recent_errors)} errors "
                f"in last {self.error_window} seconds"
            )
    
    def _record_error(self, error: str):
        """Record an error for circuit breaker tracking."""
        self.recent_errors.append(datetime.utcnow())
        self.logger.error(f"LLM call error: {error}")
    
    def get_budget_status(self) -> Dict[str, Any]:
        """Get current budget status."""
        return self.cost_tracker.get_summary()
    
    def add_custom_budget(
        self,
        limit: float,
        unit: CostUnit,
        period: timedelta,
        strict: bool = True
    ):
        """Add a custom budget constraint."""
        self.cost_tracker.add_budget(Budget(
            limit=limit,
            unit=unit,
            period=period,
            strict=strict
        ))
    
    async def process_message(self, topic: str, message: Dict[str, Any]) -> bool:
        """Process messages with budget awareness."""
        # Check if this is a budget query
        if topic == f"budget/query/{self.agent_id}":
            status = self.get_budget_status()
            await self.publish(f"budget/status/{self.agent_id}", status)
            return True
        
        # For other messages, check if we have budget to process
        try:
            self.cost_tracker.check_budgets()
        except BudgetExceededException as e:
            self.logger.warning(f"Cannot process message due to budget: {e}")
            await self.publish(f"budget/exceeded/{self.agent_id}", {
                "error": str(e),
                "status": self.get_budget_status()
            })
            return False
        
        return await super().process_message(topic, message)