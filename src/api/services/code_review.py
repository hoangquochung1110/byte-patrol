# Integration with byte_patrol core
import logging

from byte_patrol.prompt_engine.prompt_templates import (
    CodeReview,
    CodeSuggestion,
    code_review_prompt,
    code_suggestion_prompt
)
from byte_patrol.config import get_llm


logger = logging.getLogger("byte-patrol.code_review")

class CodeReviewService:
    def __init__(self):
        pass

    async def review_code(
        self,
        content,
        filename,
        areas,
        style,
    ) -> str:
        """
        Review code using the byte-patrol core logic.
        
        Args:
            content: The file content to review
            filename: The name of the file
            areas: Optional list of areas to review; if None, default areas based on file type
            
        Returns:
            Formatted review results as markdown
        """
        try:
            logger.info(f"Reviewing file: {filename}")
            
            # Get configured LLM
            llm = get_llm(
                request_timeout=30,
                max_tokens=1000
            )
            
            # Determine review areas: use provided or default based on file type
            areas_to_use = areas if areas is not None else self._get_review_areas(filename)
            
            # Structure review style
            if style is None:
                style = "Focus on actionable suggestions."

            # Setup structured output capabilities
            review_llm = llm.with_structured_output(CodeReview)
            suggestion_llm = llm.with_structured_output(CodeSuggestion)
            
            # Run the LLM pipeline with structured outputs
            areas_str = ", ".join(areas_to_use)
            review_result = (code_review_prompt | review_llm).invoke(
                {"code": content, "areas": areas_str, "style": style}
            )
            
            suggestion_result = (code_suggestion_prompt | suggestion_llm).invoke(
                {"code_review": review_result.model_dump_json()}
            )
            
            # Format the results as markdown
            return self._format_review_results(
                review_result, 
                suggestion_result, 
                filename
            )
            
        except Exception as e:
            logger.exception(f"Error reviewing code: {str(e)}")
            return f"⚠️ Error during code review: {str(e)}"
    
    def _get_review_areas(self, filename: str) -> list[str]:
        """Determine review areas based on file type"""
        # Default review areas
        areas = ["code quality", "best practices"]
        
        # Add specific areas based on file extension
        ext = filename.split(".")[-1].lower()
        
        if ext == "py":
            areas.extend(["python", "documentation", "variable naming"])
        elif ext in ["js", "ts"]:
            areas.extend(["javascript", "typescript"])
        elif ext in ["html", "css"]:
            areas.extend(["web", "ui"])
        
        return areas
    
    def _format_review_results(
        self, 
        review: CodeReview, 
        suggestion: CodeSuggestion,
        filename: str
    ) -> str:
        """Format review results as markdown"""
        rating_emoji = "🟢" if review.rating >= 8 else "🟡" if review.rating >= 5 else "🔴"
        
        result = [
            f"### Byte Patrol Code Review: `{filename}`",
            f"\n**Quality Rating**: {rating_emoji} {review.rating}/10\n",
            "#### Issues Identified:"
        ]
        
        if not review.issues:
            result.append("\n✅ No significant issues found.\n")
        else:
            for i, issue in enumerate(review.issues, 1):
                result.append(f"\n{i}. {issue}")
        
        result.append("\n#### Suggestions for Improvement:\n")
        result.append(suggestion.suggestion)
        
        return "\n".join(result)