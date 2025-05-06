# Integration with byte_patrol core
import logging
from pathlib import Path

from byte_patrol.prompt_engine.prompt_templates import (
    CodeReview,
    CodeSuggestion,
    code_review_prompt,
    code_suggestion_prompt
)
from byte_patrol.config import get_llm


logger = logging.getLogger("byte-patrol.code_review")


DEFAULT_REVIEW_STYLE = "Concise"
DEFAULT_FILE_TYPES = ("py",)


class CodeReviewService:
    def __init__(self):
        self.allowed_file_types = DEFAULT_FILE_TYPES  # Default to Python files only

    def set_allowed_file_types(self, file_types: list[str]):
        """Set the allowed file types for review"""
        self.allowed_file_types = [ft.lstrip('.') for ft in file_types]

    def can_review_file(self, filename: str) -> bool:
        """Check if a file can be reviewed based on its extension"""
       ext = Path(filename).suffix.lstrip('.').lower()
       return ext in self.allowed_file_types

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
            style: Optional style guidance for the review
            
        Returns:
            Formatted review results as markdown
        """
        try:
            if not self.can_review_file(filename):
                logger.debug(f"Skipping review: File type not supported for {filename}")
                return f"⚠️ Skipping review: File type not supported for {filename}"

            logger.info(f"Reviewing file: {filename}")
            
            # Get configured LLM
            llm = get_llm(
                request_timeout=30,
                max_tokens=5000
            )
            
            # Determine review areas: use provided or default based on file type
            areas_to_use = areas if areas is not None else self._get_review_areas(filename)
            
            # Structure review style
            if style is None:
                style = DEFAULT_REVIEW_STYLE

            # Setup structured output capabilities
            review_llm = llm.with_structured_output(CodeReview)
            suggestion_llm = llm.with_structured_output(CodeSuggestion)
            
            # Run the LLM pipeline with structured outputs
            areas_str = ", ".join(areas_to_use)
            try:
                review_result = (code_review_prompt | review_llm).invoke(
                    {"code": content, "areas": areas_str, "style": style}
                )
            except TypeError as e:
                logger.error(f"Type error during code review for {filename}: {str(e)}")
                return f"⚠️ Error during code review: {str(e)}"
            except Exception as e:
                logger.error(f"Unexpected error during code review for {filename}: {str(e)}")
                return f"⚠️ Error during code review: {str(e)}"
            else:
                try:
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
                    logger.error(f"Failed to generate suggestions for {filename}: {str(e)}")
                    return f"⚠️ Error generating suggestions: {str(e)}"
            
        except Exception as e:
            logger.exception(f"Critical error reviewing {filename}: {str(e)}")
            return f"⚠️ Error during code review: {str(e)}"
    
    def _get_review_areas(self, filename: str) -> list[str]:
        """Determine review areas based on file type"""
        # Default review areas
        areas = ["code quality"]        
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
