import logging
import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from docx import Document
from cv_manager.models import UploadedResume, ParsedResume
import os

logger = logging.getLogger(__name__)

# ---------------- ResumeParser Class ---------------- #
class ResumeParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self.text = self._extract_text()

    # ---------------- Extract text ---------------- #
    def _extract_text(self):
        ext = os.path.splitext(self.file_path)[1].lower()  # get extension in lowercase
        if ext == ".pdf":
            text = self._extract_from_pdf(self.file_path)
            if not text:
                text = self._extract_from_scanned_pdf(self.file_path)
            return text
        elif ext == ".docx":
            return self._extract_from_docx(self.file_path)
        else:
            logger.warning(f"⚠️ Unsupported file type: {ext}")
            return None


    def _extract_from_pdf(self, file_path):
        try:
            text = ""
            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                    else:
                        logger.warning(f"Page {i+1} has no text")
            if not text:
                logger.warning("PDF has no extractable text, trying OCR...")
            return text.strip()
        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            return None


    def _extract_from_scanned_pdf(self, file_path):
        try:
            text = ""
            pages = convert_from_path(file_path)
            for page in pages:
                text += pytesseract.image_to_string(page) + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"OCR extraction error: {e}")
            return None

    def _extract_from_docx(self, file_path):
        try:
            doc = Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            logger.error(f"DOCX extraction error: {e}")
            return None


# ---------------- parse_uploaded_resume Function ---------------- #
def parse_uploaded_resume(uploaded_resume_id, user=None):
    """
    Extract text -> save metadata + text into ParsedResume
    Overwrites previous resume if the same user uploads again.
    """
    try:
        uploaded_resume = UploadedResume.objects.get(id=uploaded_resume_id)
        parser = ResumeParser(uploaded_resume.file.path)
        extracted_text = parser.text or ""

        metadata_json = {
            "file_name": uploaded_resume.original_name,
            "file_path": uploaded_resume.file.url,
            "size": uploaded_resume.size,
            "extracted_text": extracted_text
        }

        # ✅ If user exists, delete their old parsed resume (overwrite)
        if user:
            old_parsed = ParsedResume.objects.filter(user=user).first()
            if old_parsed:
                old_parsed.uploaded_resume.file.delete(save=False)
                old_parsed.uploaded_resume.delete()
                old_parsed.delete()

        # ✅ Create new ParsedResume (linked to user if provided)
        parsed_resume = ParsedResume.objects.create(
            user=user if user else None,
            uploaded_resume=uploaded_resume,
            raw_text=extracted_text,
            raw_json=metadata_json
        )

        return {
            "success": True,
            "resume_id": parsed_resume.id,
            "raw_text": extracted_text,        # <--- add this
            "raw_json": metadata_json
        }

    except UploadedResume.DoesNotExist:
        return {"success": False, "error": "Uploaded resume not found"}
    except Exception as e:
        logger.error(f"Error parsing resume: {e}")
        return {"success": False, "error": str(e)}
