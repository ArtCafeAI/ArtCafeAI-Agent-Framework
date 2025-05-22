"""
Verified Agent - Agent with built-in verification and ground truth checks.

Implements Anthropic's recommendation to include verification at each step
to prevent error propagation in autonomous agents.
"""

import asyncio
from typing import Optional, Dict, Any, Callable, List, Tuple
from dataclasses import dataclass
from datetime import datetime
from .enhanced_agent import EnhancedAgent


@dataclass
class VerificationResult:
    """Result of a verification check."""
    passed: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class VerificationError(Exception):
    """Raised when verification fails and cannot proceed."""
    pass


class VerifiedAgent(EnhancedAgent):
    """
    An agent that includes verification checks at each processing step.
    
    This helps prevent error propagation and ensures reliability in
    autonomous agent systems.
    
    Example:
        ```python
        class DataAgent(VerifiedAgent):
            @verify_input(lambda x: x.get("data") is not None)
            @verify_output(lambda x: "processed" in x)
            async def process_data(self, message):
                return {"processed": message["data"].upper()}
        ```
    """
    
    def __init__(
        self,
        agent_id: str = None,
        agent_type: str = "verified",
        fail_fast: bool = True,
        **kwargs
    ):
        """
        Initialize a verified agent.
        
        Args:
            agent_id: Agent identifier
            agent_type: Type of agent
            fail_fast: Stop processing on first verification failure
            **kwargs: Additional configuration
        """
        super().__init__(agent_id=agent_id, agent_type=agent_type, **kwargs)
        
        self.fail_fast = fail_fast
        self.verification_history: List[VerificationResult] = []
        self.max_history = kwargs.get("max_verification_history", 100)
        
        # Verification rules by topic pattern
        self.input_verifiers: Dict[str, List[Callable]] = {}
        self.output_verifiers: Dict[str, List[Callable]] = {}
        self.process_verifiers: Dict[str, List[Callable]] = {}
        
        # Global verifiers applied to all messages
        self.global_input_verifiers: List[Callable] = []
        self.global_output_verifiers: List[Callable] = []
        
        # Verification metrics
        self.verification_stats = {
            "total_checks": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0
        }
        
        self.add_capability("verification")
        self.add_capability("ground_truth_checks")
    
    def add_input_verifier(
        self,
        verifier: Callable[[Dict[str, Any]], bool],
        topic_pattern: str = "*"
    ):
        """
        Add an input verification function.
        
        Args:
            verifier: Function that returns True if input is valid
            topic_pattern: Topic pattern to apply this verifier to
        """
        if topic_pattern == "*":
            self.global_input_verifiers.append(verifier)
        else:
            if topic_pattern not in self.input_verifiers:
                self.input_verifiers[topic_pattern] = []
            self.input_verifiers[topic_pattern].append(verifier)
    
    def add_output_verifier(
        self,
        verifier: Callable[[Any], bool],
        topic_pattern: str = "*"
    ):
        """
        Add an output verification function.
        
        Args:
            verifier: Function that returns True if output is valid
            topic_pattern: Topic pattern to apply this verifier to
        """
        if topic_pattern == "*":
            self.global_output_verifiers.append(verifier)
        else:
            if topic_pattern not in self.output_verifiers:
                self.output_verifiers[topic_pattern] = []
            self.output_verifiers[topic_pattern].append(verifier)
    
    def add_process_verifier(
        self,
        verifier: Callable[[str, Dict[str, Any], Any], bool],
        topic_pattern: str = "*"
    ):
        """
        Add a process verification function.
        
        Args:
            verifier: Function that validates the entire process
            topic_pattern: Topic pattern to apply this verifier to
        """
        if topic_pattern not in self.process_verifiers:
            self.process_verifiers[topic_pattern] = []
        self.process_verifiers[topic_pattern].append(verifier)
    
    async def verify_input(
        self,
        topic: str,
        message: Dict[str, Any]
    ) -> VerificationResult:
        """
        Verify input message before processing.
        
        Args:
            topic: Message topic
            message: Input message
            
        Returns:
            VerificationResult
        """
        self.verification_stats["total_checks"] += 1
        
        try:
            # Check global verifiers
            for verifier in self.global_input_verifiers:
                if not verifier(message):
                    result = VerificationResult(
                        passed=False,
                        message=f"Global input verification failed: {verifier.__name__}",
                        details={"topic": topic, "message": message}
                    )
                    self._record_verification(result)
                    return result
            
            # Check topic-specific verifiers
            for pattern, verifiers in self.input_verifiers.items():
                if self._matches_topic_pattern(pattern, topic):
                    for verifier in verifiers:
                        if not verifier(message):
                            result = VerificationResult(
                                passed=False,
                                message=f"Input verification failed: {verifier.__name__}",
                                details={"topic": topic, "pattern": pattern}
                            )
                            self._record_verification(result)
                            return result
            
            result = VerificationResult(
                passed=True,
                message="Input verification passed",
                details={"topic": topic}
            )
            self._record_verification(result)
            return result
            
        except Exception as e:
            self.verification_stats["errors"] += 1
            result = VerificationResult(
                passed=False,
                message=f"Input verification error: {str(e)}",
                details={"topic": topic, "error": str(e)}
            )
            self._record_verification(result)
            return result
    
    async def verify_output(
        self,
        topic: str,
        output: Any
    ) -> VerificationResult:
        """
        Verify output before returning/publishing.
        
        Args:
            topic: Message topic
            output: Output to verify
            
        Returns:
            VerificationResult
        """
        self.verification_stats["total_checks"] += 1
        
        try:
            # Check global verifiers
            for verifier in self.global_output_verifiers:
                if not verifier(output):
                    result = VerificationResult(
                        passed=False,
                        message=f"Global output verification failed: {verifier.__name__}",
                        details={"topic": topic, "output_type": type(output).__name__}
                    )
                    self._record_verification(result)
                    return result
            
            # Check topic-specific verifiers
            for pattern, verifiers in self.output_verifiers.items():
                if self._matches_topic_pattern(pattern, topic):
                    for verifier in verifiers:
                        if not verifier(output):
                            result = VerificationResult(
                                passed=False,
                                message=f"Output verification failed: {verifier.__name__}",
                                details={"topic": topic, "pattern": pattern}
                            )
                            self._record_verification(result)
                            return result
            
            result = VerificationResult(
                passed=True,
                message="Output verification passed",
                details={"topic": topic}
            )
            self._record_verification(result)
            return result
            
        except Exception as e:
            self.verification_stats["errors"] += 1
            result = VerificationResult(
                passed=False,
                message=f"Output verification error: {str(e)}",
                details={"topic": topic, "error": str(e)}
            )
            self._record_verification(result)
            return result
    
    async def verify_process(
        self,
        topic: str,
        input_message: Dict[str, Any],
        output: Any
    ) -> VerificationResult:
        """
        Verify the entire processing chain.
        
        Args:
            topic: Message topic
            input_message: Original input
            output: Processing output
            
        Returns:
            VerificationResult
        """
        self.verification_stats["total_checks"] += 1
        
        try:
            for pattern, verifiers in self.process_verifiers.items():
                if self._matches_topic_pattern(pattern, topic):
                    for verifier in verifiers:
                        if not verifier(topic, input_message, output):
                            result = VerificationResult(
                                passed=False,
                                message=f"Process verification failed: {verifier.__name__}",
                                details={
                                    "topic": topic,
                                    "pattern": pattern,
                                    "has_output": output is not None
                                }
                            )
                            self._record_verification(result)
                            return result
            
            result = VerificationResult(
                passed=True,
                message="Process verification passed",
                details={"topic": topic}
            )
            self._record_verification(result)
            return result
            
        except Exception as e:
            self.verification_stats["errors"] += 1
            result = VerificationResult(
                passed=False,
                message=f"Process verification error: {str(e)}",
                details={"topic": topic, "error": str(e)}
            )
            self._record_verification(result)
            return result
    
    async def process_message_with_verification(
        self,
        topic: str,
        message: Dict[str, Any]
    ) -> Tuple[bool, Optional[Any]]:
        """
        Process a message with full verification pipeline.
        
        Args:
            topic: Message topic
            message: Message to process
            
        Returns:
            Tuple of (success, result)
        """
        # Step 1: Verify input
        input_result = await self.verify_input(topic, message)
        if not input_result.passed:
            if self.fail_fast:
                raise VerificationError(f"Input verification failed: {input_result.message}")
            else:
                await self.handle_verification_failure("input", input_result)
                return False, None
        
        # Step 2: Process message
        try:
            # Call the actual process_message method
            processed = await super().process_message(topic, message)
            output = self._last_message_output if hasattr(self, "_last_message_output") else None
        except Exception as e:
            self.logger.error(f"Processing error: {str(e)}", exc_info=True)
            if self.fail_fast:
                raise
            return False, None
        
        # Step 3: Verify output if there is one
        if output is not None:
            output_result = await self.verify_output(topic, output)
            if not output_result.passed:
                if self.fail_fast:
                    raise VerificationError(f"Output verification failed: {output_result.message}")
                else:
                    await self.handle_verification_failure("output", output_result)
                    return False, None
        
        # Step 4: Verify the entire process
        process_result = await self.verify_process(topic, message, output)
        if not process_result.passed:
            if self.fail_fast:
                raise VerificationError(f"Process verification failed: {process_result.message}")
            else:
                await self.handle_verification_failure("process", process_result)
                return False, None
        
        return processed, output
    
    async def process_message(self, topic: str, message: Dict[str, Any]) -> bool:
        """Override to add verification."""
        processed, _ = await self.process_message_with_verification(topic, message)
        return processed
    
    async def handle_verification_failure(
        self,
        stage: str,
        result: VerificationResult
    ):
        """
        Handle verification failures.
        
        Override this method to implement custom failure handling.
        
        Args:
            stage: Verification stage (input, output, process)
            result: Verification result
        """
        self.logger.warning(
            f"Verification failed at {stage}: {result.message}",
            extra={"details": result.details}
        )
        
        # Publish verification failure event
        await self.publish(f"verification/failure/{self.agent_id}", {
            "stage": stage,
            "result": {
                "passed": result.passed,
                "message": result.message,
                "details": result.details,
                "timestamp": result.timestamp.isoformat()
            },
            "agent_id": self.agent_id
        })
    
    def _record_verification(self, result: VerificationResult):
        """Record verification result for history and metrics."""
        self.verification_history.append(result)
        
        # Maintain history size limit
        if len(self.verification_history) > self.max_history:
            self.verification_history.pop(0)
        
        # Update metrics
        if result.passed:
            self.verification_stats["passed"] += 1
        else:
            self.verification_stats["failed"] += 1
    
    def _matches_topic_pattern(self, pattern: str, topic: str) -> bool:
        """Check if topic matches pattern (supports wildcards)."""
        if pattern == "*":
            return True
        if pattern == topic:
            return True
        
        # Simple wildcard matching
        if pattern.endswith("/*"):
            prefix = pattern[:-2]
            return topic.startswith(prefix + "/")
        
        return False
    
    def get_verification_stats(self) -> Dict[str, Any]:
        """Get verification statistics."""
        total = self.verification_stats["total_checks"]
        success_rate = (
            self.verification_stats["passed"] / total if total > 0 else 0
        )
        
        return {
            **self.verification_stats,
            "success_rate": success_rate,
            "history_size": len(self.verification_history)
        }


def verify_input(verifier: Callable[[Dict[str, Any]], bool]):
    """
    Decorator to add input verification to a method.
    
    Example:
        ```python
        @verify_input(lambda x: "required_field" in x)
        async def process_data(self, message):
            return message["required_field"]
        ```
    """
    def decorator(func):
        func._input_verifier = verifier
        return func
    return decorator


def verify_output(verifier: Callable[[Any], bool]):
    """
    Decorator to add output verification to a method.
    
    Example:
        ```python
        @verify_output(lambda x: x is not None and len(x) > 0)
        async def generate_response(self, prompt):
            return await self.llm.generate(prompt)
        ```
    """
    def decorator(func):
        func._output_verifier = verifier
        return func
    return decorator