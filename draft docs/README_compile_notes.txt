SEQ-REFACTOR — deliverables
===========================

1. SEQ_REFACTOR_paper.tex
   IEEE research paper (IEEEtran). Compile on Overleaf:
     - New Project > Blank Project > upload this .tex
     - Menu > Compiler: pdfLaTeX  (uses the built-in bibliography; no .bib needed)
     - Recompile
   The file is set single-column 11pt for readable review. For the two-column
   IEEE camera-ready layout, change ONE line at the top:
       \documentclass[journal,onecolumn,11pt]{IEEEtran}
   to
       \documentclass[journal]{IEEEtran}
   Local build (optional): needs texlive-publishers (ieeetran), algorithm2e,
   amsthm, booktabs. Verified to compile with 0 errors and 0 undefined
   references; 28 references, all cited.

2. SEQ_REFACTOR_Software_Specification.docx
   Implementation spec for a coding agent (e.g. Claude Code) to build the tool
   and run the experiments. Open in Word; the Table of Contents populates via
   right-click > Update Field (Word computes TOC/page-number fields on open;
   headless converters do not). Section 11 is the ordered, copy-pasteable build
   plan; Section 7 is the ordering algorithm to implement exactly.

Constraints honoured: no em-dashes in either document; the pilot is reported as
a single directional case with no fabricated aggregate results; supervisor
doc. Ing. Ivan Polasek, PhD is cited and acknowledged; PhD / Comenius branding.
