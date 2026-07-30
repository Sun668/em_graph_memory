"""Thin orchestration around the vendored official LoCoMo QA code."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Mapping, Optional
from unittest.mock import patch

import numpy as np

from locomo_eval.recall import QARecall
from locomo_eval.vendor_runtime import load_official_modules


@dataclass(frozen=True)
class LoCoMoEvaluationConfig:
    model: str = "gpt-3.5-turbo"
    top_k: int = 25
    rag_mode: str = "dialog"
    batch_size: int = 1

    @property
    def model_key(self) -> str:
        return f"{self.model}_{self.rag_mode}_top_{self.top_k}"

    @property
    def prediction_key(self) -> str:
        return f"{self.model_key}_prediction"


class OfficialLoCoMoEvaluator:
    """Run official QA generation/scoring with retrieval supplied by QARecall."""

    def __init__(
        self,
        recall: QARecall,
        config: Optional[LoCoMoEvaluationConfig] = None,
    ):
        self.recall = recall
        self.config = config or LoCoMoEvaluationConfig()
        if self.config.batch_size != 1:
            raise ValueError("Official LoCoMo RAG evaluation requires batch_size=1")

    def _args(self) -> SimpleNamespace:
        return SimpleNamespace(
            data_file="",
            out_file="",
            model=self.config.model,
            use_rag=True,
            use_4bit=False,
            batch_size=self.config.batch_size,
            rag_mode=self.config.rag_mode,
            emb_dir="",
            top_k=self.config.top_k,
            retriever="injected_qa_recall",
            overwrite=True,
        )

    def evaluate_sample(
        self,
        sample: Mapping[str, Any],
    ) -> Dict[str, Any]:
        evaluation, _evaluation_stats, gpt_utils = load_official_modules()
        source = copy.deepcopy(dict(sample))
        out_data: Dict[str, Any] = {
            "sample_id": source["sample_id"],
            "qa": copy.deepcopy(source.get("qa") or []),
        }
        qa_rows = source.get("qa") or []

        def _prepare_for_rag(_args: Any, data: Mapping[str, Any]):
            return data, np.arange(len(data.get("qa") or []), dtype=np.int64)

        def _get_rag_context(
            context_database: Mapping[str, Any],
            query_vector: Any,
            args: Any,
        ):
            qa_index = int(query_vector)
            question = str(context_database["qa"][qa_index]["question"])
            recalled = self.recall.recall(
                context_database,
                qa_index,
                question,
                int(args.top_k),
            )
            return str(recalled.context), list(recalled.context_ids)

        with patch.object(gpt_utils, "prepare_for_rag", _prepare_for_rag), patch.object(
            gpt_utils,
            "get_rag_context",
            _get_rag_context,
        ):
            answers = gpt_utils.get_gpt_answers(
                source,
                out_data,
                self.config.prediction_key,
                self._args(),
            )

        f1_values, _lengths, recall_values = evaluation.eval_question_answering(
            answers["qa"],
            self.config.prediction_key,
        )
        for index, row in enumerate(answers["qa"]):
            row[f"{self.config.model_key}_f1"] = round(f1_values[index], 3)
            row[f"{self.config.model_key}_recall"] = round(
                recall_values[index], 3
            )
        return answers

    def evaluate_dataset(
        self,
        samples: Iterable[Mapping[str, Any]],
        *,
        output_file: Optional[Path] = None,
        annotation_file: Optional[Path] = None,
        stats_file: Optional[Path] = None,
    ) -> List[Dict[str, Any]]:
        outputs = [self.evaluate_sample(sample) for sample in samples]
        if output_file is not None:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(
                json.dumps(outputs, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        if stats_file is not None:
            if output_file is None or annotation_file is None:
                raise ValueError(
                    "official stats require output_file and annotation_file"
                )
            _evaluation, evaluation_stats, _gpt_utils = load_official_modules()
            evaluation_stats.analyze_aggr_acc(
                str(annotation_file),
                str(output_file),
                str(stats_file),
                self.config.model_key,
                f"{self.config.model_key}_f1",
                rag=True,
            )
        return outputs

