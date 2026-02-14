# interviews/services/evaluation_service.py
import difflib
import json
from typing import Dict, List, Tuple
from django.db.models import Q

class AnswerEvaluationService:
    """Service for automated answer evaluation"""
    
    @staticmethod
    def evaluate_descriptive_answer(candidate_answer: str, hr_answer: str, criteria: Dict) -> Dict:
        """
        Evaluate descriptive answers using multiple techniques
        
        Args:
            candidate_answer: Candidate's answer text
            hr_answer: HR's expected answer
            criteria: Evaluation criteria including keywords, min_length, etc.
        
        Returns:
            Dict with score, feedback, and match details
        """
        candidate_answer = candidate_answer.lower().strip()
        hr_answer = hr_answer.lower().strip()
        
        # 1. Keyword matching
        required_keywords = criteria.get('required_keywords', [])
        optional_keywords = criteria.get('optional_keywords', [])
        
        found_required = []
        missing_required = []
        
        for keyword in required_keywords:
            if keyword.lower() in candidate_answer:
                found_required.append(keyword)
            else:
                missing_required.append(keyword)
        
        found_optional = [kw for kw in optional_keywords if kw.lower() in candidate_answer]
        
        # 2. Text similarity (using difflib)
        similarity = difflib.SequenceMatcher(
            None, 
            candidate_answer, 
            hr_answer
        ).ratio()
        
        # 3. Length check
        min_length = criteria.get('min_length', 50)
        max_length = criteria.get('max_length', 1000)
        answer_length = len(candidate_answer)
        
        # 4. Calculate score
        base_score = 0.0
        
        # Keyword score (50% of total)
        keyword_score = 0.0
        if required_keywords:
            keyword_score = (len(found_required) / len(required_keywords)) * 0.5
        
        # Similarity score (30% of total)
        similarity_score = similarity * 0.3
        
        # Length score (20% of total)
        length_score = 0.0
        if min_length <= answer_length <= max_length:
            length_score = 0.2
        elif answer_length < min_length:
            length_score = 0.1  # Partial credit
        else:
            length_score = 0.15  # Partial credit for long answers
        
        total_score = min(1.0, keyword_score + similarity_score + length_score)
        
        # 5. Generate feedback
        feedback_parts = []
        
        if found_required:
            feedback_parts.append(f"Good job covering: {', '.join(found_required[:3])}")
        
        if missing_required:
            feedback_parts.append(f"Missing key points: {', '.join(missing_required[:3])}")
        
        if found_optional:
            feedback_parts.append(f"Bonus points for: {', '.join(found_optional[:2])}")
        
        if similarity > 0.7:
            feedback_parts.append("Your answer closely matches expected concepts")
        elif similarity < 0.3:
            feedback_parts.append("Consider reviewing the topic more thoroughly")
        
        if answer_length < min_length:
            feedback_parts.append(f"Try to provide more detail (minimum {min_length} characters)")
        elif answer_length > max_length:
            feedback_parts.append("Your answer is quite detailed, but could be more concise")
        
        return {
            'score': round(total_score * 100, 2),  # Convert to percentage
            'score_breakdown': {
                'keyword_score': round(keyword_score * 100, 2),
                'similarity_score': round(similarity_score * 100, 2),
                'length_score': round(length_score * 100, 2)
            },
            'keyword_analysis': {
                'found_required': found_required,
                'missing_required': missing_required,
                'found_optional': found_optional
            },
            'similarity_ratio': round(similarity, 3),
            'answer_length': answer_length,
            'feedback': ' | '.join(feedback_parts) if feedback_parts else 'Answer submitted successfully',
            'needs_hr_review': similarity < 0.5 or len(missing_required) > 0
        }
    
    @staticmethod
    def evaluate_code_answer(candidate_code: str, expected_output: str, test_cases: List[Dict]) -> Dict:
        """
        Evaluate coding answers (simplified - full implementation would need code execution)
        
        Args:
            candidate_code: Candidate's code submission
            expected_output: Expected output
            test_cases: List of test cases to run
        
        Returns:
            Dict with evaluation results
        """
        # In production, this would execute code in a sandbox
        # For now, we'll do static analysis
        
        analysis = {
            'score': 0.0,
            'test_cases_passed': 0,
            'total_test_cases': len(test_cases),
            'syntax_errors': [],
            'complexity_analysis': {},
            'feedback': []
        }
        
        # Check for syntax (basic)
        try:
            # In production: ast.parse(candidate_code)
            has_syntax = True
        except SyntaxError as e:
            analysis['syntax_errors'].append(str(e))
            analysis['feedback'].append(f"Syntax error: {e}")
            has_syntax = False
        
        # Check code structure
        lines = candidate_code.split('\n')
        analysis['line_count'] = len(lines)
        
        # Look for common patterns
        if 'def ' in candidate_code:
            analysis['feedback'].append("Good job using functions")
        
        if 'import ' in candidate_code:
            analysis['feedback'].append("Appropriate use of imports")
        
        # Simple keyword checking
        required_keywords = ['def', 'return', 'if', 'for', 'while']  # Example
        found_keywords = [kw for kw in required_keywords if kw in candidate_code]
        
        if has_syntax and len(found_keywords) >= 2:
            # Base score for syntactically correct code with structure
            analysis['score'] = 30.0  # 30% base score
            
            # Additional points for test cases (mock)
            # In production, this would actually run the code
            mock_passed = min(2, len(test_cases))  # Mock passing 2 test cases
            analysis['test_cases_passed'] = mock_passed
            analysis['score'] += (mock_passed / len(test_cases)) * 70 if test_cases else 0
            
            analysis['feedback'].append(f"Passed {mock_passed}/{len(test_cases)} test cases")
        else:
            analysis['feedback'].append("Code needs more structure")
        
        return analysis
    
    @staticmethod
    def batch_evaluate_answers(interview_id: str) -> Dict:
        """
        Batch evaluate all answers for an interview
        
        Returns:
            Dict with overall evaluation results
        """
        from ..models import Interview, CandidateAnswer
        
        try:
            interview = Interview.objects.get(id=interview_id)
        except Interview.DoesNotExist:
            return {'error': 'Interview not found'}
        
        answers = CandidateAnswer.objects.filter(
            question_set__interview=interview,
            is_submitted=True
        ).select_related('question_set__question')
        
        results = {
            'total_questions': answers.count(),
            'evaluated_questions': 0,
            'auto_graded_questions': 0,
            'needs_hr_review': 0,
            'category_scores': {},
            'question_results': []
        }
        
        for answer in answers:
            question = answer.question_set.question
            
            # Skip already graded
            if answer.hr_score is not None:
                results['evaluated_questions'] += 1
                continue
            
            evaluation = None
            
            # Auto-grade based on question type
            if question.question_type.code == 'MCQ':
                # Already auto-graded by CandidateAnswer.calculate_auto_score()
                results['auto_graded_questions'] += 1
                evaluation = {
                    'score': answer.auto_score,
                    'is_auto_graded': True,
                    'needs_hr_review': False
                }
            
            elif question.question_type.code == 'DESC':
                # Evaluate descriptive answer
                criteria = {
                    'required_keywords': question.tags[:5],  # Use tags as keywords
                    'min_length': 50,
                    'max_length': 1000
                }
                
                evaluation = AnswerEvaluationService.evaluate_descriptive_answer(
                    answer.answer_text,
                    question.hr_answer,
                    criteria
                )
                
                # Update answer with auto-score
                answer.auto_score = evaluation['score']
                answer.feedback_notes = evaluation.get('feedback', '')
                answer.save()
                
                results['auto_graded_questions'] += 1
                if evaluation.get('needs_hr_review', False):
                    results['needs_hr_review'] += 1
            
            elif question.question_type.code == 'CODE':
                # Evaluate code answer
                test_cases = question.options if question.options else []
                evaluation = AnswerEvaluationService.evaluate_code_answer(
                    answer.code_snippet,
                    question.hr_answer,
                    test_cases
                )
                
                answer.auto_score = evaluation['score']
                answer.feedback_notes = ' | '.join(evaluation.get('feedback', []))
                answer.save()
                
                results['auto_graded_questions'] += 1
                results['needs_hr_review'] += 1  # Code always needs HR review
            
            if evaluation:
                results['question_results'].append({
                    'question_id': str(question.id),
                    'question_type': question.question_type.code,
                    'score': evaluation.get('score', 0),
                    'is_auto_graded': evaluation.get('is_auto_graded', False),
                    'needs_hr_review': evaluation.get('needs_hr_review', True)
                })
                
                # Update category scores
                category = question.category.name
                if category not in results['category_scores']:
                    results['category_scores'][category] = {
                        'total_score': 0,
                        'question_count': 0
                    }
                
                results['category_scores'][category]['total_score'] += evaluation.get('score', 0)
                results['category_scores'][category]['question_count'] += 1
        
        # Calculate average category scores
        for category, data in results['category_scores'].items():
            if data['question_count'] > 0:
                data['average_score'] = round(data['total_score'] / data['question_count'], 2)
        
        return results