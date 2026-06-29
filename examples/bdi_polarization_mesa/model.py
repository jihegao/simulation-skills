"""BDI-style opinion polarization model with recommendation and group action.

This is an exploratory mechanism model. A small fraction of agents can use
behavior profiles sampled by the local opencode CLI before a batch run starts.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import fmean

import mesa

from examples.bdi_polarization_mesa.opencode_sampler import FALLBACK_BEHAVIOR_SAMPLES


def _clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _sign(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


@dataclass
class ContentItem:
    stance: float
    popularity: float = 1.0


class BDIAgent:
    """Belief-desire-intention agent for a one-dimensional issue space."""

    def __init__(
        self,
        unique_id: int,
        model: "BDIPolarizationModel",
        belief: float,
        action_threshold: float,
        social_fit_desire: float,
        credulity: float,
        activism: float,
        llm_sample: dict[str, float | str] | None = None,
    ) -> None:
        self.unique_id = unique_id
        self.model = model
        self.belief = belief
        self.action_threshold = action_threshold
        self.social_fit_desire = social_fit_desire
        self.credulity = credulity
        self.activism = activism
        self.llm_sample = llm_sample
        self.last_intention = "idle"
        self.last_consumed_alignment = 0.0

    @property
    def is_llm_sampled(self) -> bool:
        return self.llm_sample is not None

    def _desire_for_action(self, local_alignment: float) -> float:
        intensity = abs(self.belief)
        social_pressure = max(0.0, local_alignment) * self.social_fit_desire
        activism = self.activism
        if self.llm_sample is not None:
            activism = float(self.llm_sample["activism"])
        return intensity * (0.65 + activism) + social_pressure

    def _intention_from_desires(self, local_alignment: float) -> str:
        action_drive = self._desire_for_action(local_alignment)
        if action_drive >= self.action_threshold + 0.22:
            return "mobilize"
        if action_drive >= self.action_threshold:
            return "share"
        if abs(self.belief) >= self.action_threshold * 0.75:
            return "support"
        return "idle"

    def choose_content(self, candidates: list[ContentItem]) -> ContentItem:
        weights: list[float] = []
        for item in candidates:
            similarity = 1.0 - min(1.0, abs(self.belief - item.stance) / 2.0)
            popularity = math.log1p(item.popularity)
            novelty = abs(item.stance - self.belief)
            moderation = 1.0 - abs(item.stance)
            if self.llm_sample is None:
                llm_novelty = 0.0
                llm_moderation = 0.0
            else:
                llm_novelty = float(self.llm_sample["novelty_bias"]) * novelty
                llm_moderation = float(self.llm_sample["moderation_bias"]) * moderation
            recommendation = (
                self.model.recommendation_strength * (similarity + 0.35 * popularity)
                + (1.0 - self.model.recommendation_strength) * self.model.rng.random()
            )
            weights.append(max(0.01, recommendation + llm_novelty + llm_moderation))
        return self.model.rng.choices(candidates, weights=weights, k=1)[0]

    def step(self) -> None:
        candidates = self.model.recommend_items(self)
        consumed = [self.choose_content(candidates) for _ in range(self.model.items_per_step)]
        avg_stance = fmean(item.stance for item in consumed)
        self.last_consumed_alignment = fmean(
            1.0 - min(1.0, abs(self.belief - item.stance) / 2.0) for item in consumed
        )

        credulity = self.credulity if self.llm_sample is None else float(self.llm_sample["credulity"])
        dissonance = abs(avg_stance - self.belief)
        assimilation = credulity * (0.12 + 0.18 * self.model.recommendation_strength)
        contrast = max(0.0, dissonance - 0.85) * self.model.network_homophily * 0.04
        self.belief = _clamp(self.belief + assimilation * (avg_stance - self.belief))
        if _sign(avg_stance) != 0 and _sign(avg_stance) != _sign(self.belief):
            self.belief = _clamp(self.belief - contrast * _sign(avg_stance))

        local_alignment = self.model.local_alignment(self)
        self.last_intention = self._intention_from_desires(local_alignment)
        if self.last_intention in {"share", "mobilize"}:
            amplification = 1.0 if self.last_intention == "share" else 1.8
            self.model.group_actions.append(self.belief)
            self.model.content_pool.append(
                ContentItem(
                    stance=_clamp(self.belief + self.model.rng.gauss(0.0, 0.08)),
                    popularity=1.0 + amplification,
                )
            )


class BDIPolarizationModel(mesa.Model):
    """BDI agents exposed to recommender-mediated content and group action."""

    def __init__(
        self,
        population_size: int = 120,
        recommendation_strength: float = 0.65,
        network_homophily: float = 0.55,
        group_action_feedback: float = 0.35,
        llm_agent_fraction: float = 0.08,
        initial_opinion_spread: float = 0.35,
        content_pool_size: int = 80,
        items_per_step: int = 3,
        llm_behavior_samples: list[dict[str, float | str]] | None = None,
        seed: int | None = None,
    ) -> None:
        super().__init__(seed=seed)
        self.rng = random.Random(seed)
        self.population_size = int(population_size)
        self.recommendation_strength = float(recommendation_strength)
        self.network_homophily = float(network_homophily)
        self.group_action_feedback = float(group_action_feedback)
        self.llm_agent_fraction = float(llm_agent_fraction)
        self.initial_opinion_spread = float(initial_opinion_spread)
        self.content_pool_size = int(content_pool_size)
        self.items_per_step = int(items_per_step)
        self.llm_behavior_samples = list(llm_behavior_samples or FALLBACK_BEHAVIOR_SAMPLES)
        self.tick = 0
        self.group_actions: list[float] = []
        self.bdi_agents: list[BDIAgent] = []
        self.content_pool = [
            ContentItem(stance=self.rng.uniform(-1.0, 1.0), popularity=self.rng.uniform(0.7, 1.4))
            for _ in range(self.content_pool_size)
        ]
        self._create_agents()

    def _create_agents(self) -> None:
        llm_count = round(self.population_size * self.llm_agent_fraction)
        llm_ids = set(self.rng.sample(range(self.population_size), k=min(llm_count, self.population_size)))
        for idx in range(self.population_size):
            side = -1.0 if idx < self.population_size / 2 else 1.0
            belief = _clamp(side * abs(self.rng.gauss(self.initial_opinion_spread, 0.18)))
            llm_sample = self.rng.choice(self.llm_behavior_samples) if idx in llm_ids else None
            agent = BDIAgent(
                unique_id=idx,
                model=self,
                belief=belief,
                action_threshold=self.rng.uniform(0.42, 0.68),
                social_fit_desire=self.rng.uniform(0.15, 0.42),
                credulity=self.rng.uniform(0.28, 0.62),
                activism=self.rng.uniform(0.12, 0.52),
                llm_sample=llm_sample,
            )
            self.bdi_agents.append(agent)

    def recommend_items(self, agent: BDIAgent) -> list[ContentItem]:
        sample_size = min(max(8, self.items_per_step * 4), len(self.content_pool))
        candidates = self.rng.sample(self.content_pool, k=sample_size)
        candidates.sort(
            key=lambda item: (
                self.recommendation_strength * (1.0 - min(1.0, abs(agent.belief - item.stance) / 2.0))
                + self.group_action_feedback * math.log1p(item.popularity)
            ),
            reverse=True,
        )
        return candidates[: max(self.items_per_step, min(6, len(candidates)))]

    def local_alignment(self, agent: BDIAgent) -> float:
        sample = self.rng.sample(self.bdi_agents, k=min(12, len(self.bdi_agents)))
        same_side = sum(1 for other in sample if _sign(other.belief) == _sign(agent.belief))
        return same_side / max(1, len(sample))

    def step(self) -> None:
        self.tick += 1
        self.group_actions = []
        for agent in self.rng.sample(self.bdi_agents, k=len(self.bdi_agents)):
            agent.step()
        for item in self.content_pool:
            item.popularity *= 0.985
        if len(self.content_pool) > self.content_pool_size * 3:
            self.content_pool.sort(key=lambda item: item.popularity, reverse=True)
            del self.content_pool[self.content_pool_size * 2 :]

    def snapshot(self) -> dict[str, float]:
        beliefs = [agent.belief for agent in self.bdi_agents]
        left = [value for value in beliefs if value < 0]
        right = [value for value in beliefs if value >= 0]
        left_mean = fmean(left) if left else 0.0
        right_mean = fmean(right) if right else 0.0
        overall_mean = fmean(beliefs)
        variance = fmean((value - overall_mean) ** 2 for value in beliefs)
        intention_counts = {name: 0 for name in ("idle", "support", "share", "mobilize")}
        for agent in self.bdi_agents:
            intention_counts[agent.last_intention] += 1
        llm_agents = [agent for agent in self.bdi_agents if agent.is_llm_sampled]
        return {
            "tick": float(self.tick),
            "belief_mean": overall_mean,
            "belief_variance": variance,
            "polarization_index": abs(right_mean - left_mean),
            "extreme_share": sum(1 for value in beliefs if abs(value) >= 0.75) / len(beliefs),
            "action_rate": (intention_counts["share"] + intention_counts["mobilize"]) / len(self.bdi_agents),
            "mobilize_rate": intention_counts["mobilize"] / len(self.bdi_agents),
            "mean_recommendation_alignment": fmean(agent.last_consumed_alignment for agent in self.bdi_agents),
            "group_actions": float(len(self.group_actions)),
            "content_pool_size": float(len(self.content_pool)),
            "llm_sampled_agents": float(len(llm_agents)),
            "llm_mean_abs_belief": fmean(abs(agent.belief) for agent in llm_agents) if llm_agents else 0.0,
        }
