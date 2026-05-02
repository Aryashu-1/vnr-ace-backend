from typing import Any, Dict, List
import json

def generate_latex_resume(data: Dict[str, Any]) -> str:
    """
    Generates LaTeX code for a resume based on structured JSON data.
    Uses a standard, professional, ATS-friendly template.
    """
    personal = data.get("personal_info", {})
    education = data.get("education", [])
    skills = data.get("skills", [])
    projects = data.get("projects", [])
    experience = data.get("experience", [])
    achievements = data.get("achievements", [])

    latex = [
        r"\documentclass[letterpaper,11pt]{article}",
        r"\usepackage{latexsym}",
        r"\usepackage[empty]{fullpage}",
        r"\usepackage{titlesec}",
        r"\usepackage{marvosym}",
        r"\usepackage[usenames,dvipsnames]{color}",
        r"\usepackage{verbatim}",
        r"\usepackage{enumitem}",
        r"\usepackage[hidelinks]{hyperref}",
        r"\usepackage{fancyhdr}",
        r"\usepackage[english]{babel}",
        r"\usepackage{tabularx}",
        r"\input{glyphtounicode}",
        "",
        r"%----------FONT OPTIONS----------",
        r"% sans-serif",
        r"% \usepackage[sfdefault]{roboto}",
        r"% \usepackage[sfdefault]{infini}",
        r"% \usepackage[sfdefault]{Inter}",
        r"% \usepackage[sfdefault]{noto-sans}",
        r"% \usepackage[default]{sourcesanspro}",
        "",
        r"% serif",
        r"% \usepackage{CormorantGaramond}",
        r"% \usepackage{charter}",
        "",
        r"\pagestyle{fancy}",
        r"\fancyhf{}",
        r"\fancyfoot{}",
        r"\renewcommand{\headrulewidth}{0pt}",
        r"\renewcommand{\footrulewidth}{0pt}",
        "",
        r"% Adjust margins",
        r"\addtolength{\oddsidemargin}{-0.5in}",
        r"\addtolength{\evensidemargin}{-0.5in}",
        r"\addtolength{\textwidth}{1in}",
        r"\addtolength{\topmargin}{-.5in}",
        r"\addtolength{\textheight}{1.0in}",
        "",
        r"\urlstyle{same}",
        "",
        r"\raggedbottom",
        r"\raggedright",
        r"\setlength{\tabcolsep}{0in}",
        "",
        r"% Sections formatting",
        r"\titleformat{\section}{",
        r"  \vspace{-4pt}\scshape\raggedright\large",
        r"}{}{0em}{}[\color{black}\titlerule \vspace{-5pt}]",
        "",
        r"% Ensure that generate pdf is machine readable/ATS parsable",
        r"\pdfgentounicode=1",
        "",
        r"%-------------------------",
        r"% Custom commands",
        r"\newcommand{\resumeItem}[1]{",
        r"  \item\small{",
        r"    {#1 \vspace{-2pt}}",
        r"  }",
        r"}",
        "",
        r"\newcommand{\resumeSubheading}[4]{",
        r"  \vspace{-2pt}\item",
        r"    \begin{tabular*}{0.97\textwidth}[t]{l@{\extracolsep{\fill}}r}",
        r"      \textbf{#1} & #2 \\",
        r"      \textit{\small#3} & \textit{\small #4} \\",
        r"    \end{tabular*}\vspace{-7pt}",
        r"}",
        "",
        r"\newcommand{\resumeSubSubheading}[2]{",
        r"    \item",
        r"    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}",
        r"      \textit{\small#1} & \textit{\small #2} \\",
        r"    \end{tabular*}\vspace{-7pt}",
        r"}",
        "",
        r"\newcommand{\resumeProjectHeading}[2]{",
        r"    \item",
        r"    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}",
        r"      \small#1 & #2 \\",
        r"    \end{tabular*}\vspace{-7pt}",
        r"}",
        "",
        r"\newcommand{\resumeSubItem}[1]{\resumeItem{#1}\vspace{-4pt}}",
        "",
        r"\renewcommand\labelitemii{$\vcenter{\hbox{\tiny$\bullet$}}$}",
        "",
        r"\newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=0.15in, label={}]}",
        r"\newcommand{\resumeSubHeadingListEnd}{\end{itemize}}",
        r"\newcommand{\resumeItemListStart}{\begin{itemize}}",
        r"\newcommand{\resumeItemListEnd}{\end{itemize}\vspace{-5pt}}",
        "",
        r"%-------------------------------------------",
        r"%%%%%%  RESUME STARTS HERE  %%%%%%%%%%%%%%%%%%%%%%%%%%%%",
        "",
        r"\begin{document}",
        "",
        r"%----------HEADING----------",
        r"\begin{center}",
        f"    \\textbf{{\\Huge \\scshape {personal.get('name', 'Your Name')}}} \\\\ \\vspace{{1pt}}",
        f"    \\small {personal.get('phone', 'Phone')} $|$ \\href{{mailto:{personal.get('email', 'Email')}}}{{\\underline{{{personal.get('email', 'Email')}}}}} $|$ "
    ]

    # Add links
    links = personal.get('links', [])
    if isinstance(links, list):
        link_strs = []
        for link in links:
            if 'linkedin.com' in link:
                link_strs.append(f"\\href{{{link}}}{{\\underline{{linkedin.com/{link.split('/')[-1]}}}}}")
            elif 'github.com' in link:
                link_strs.append(f"\\href{{{link}}}{{\\underline{{github.com/{link.split('/')[-1]}}}}}")
            else:
                link_strs.append(f"\\href{{{link}}}{{\\underline{{{link}}}}}")
        latex[-1] += " $|$ ".join(link_strs)
    
    latex.append(r"\end{center}")
    latex.append("")

    # Education
    if education:
        latex.append(r"\section{Education}")
        latex.append(r"  \resumeSubHeadingListStart")
        for edu in education:
            inst = edu.get('institution', 'University Name')
            deg = edu.get('degree', 'Degree')
            year = edu.get('year', 'Year')
            gpa = edu.get('gpa', '')
            latex.append(f"    \\resumeSubheading{{{inst}}}{{{year}}}{{{deg}}}{{{f'GPA: {gpa}' if gpa else ''}}}")
        latex.append(r"  \resumeSubHeadingListEnd")
        latex.append("")

    # Skills
    if skills:
        latex.append(r"\section{Technical Skills}")
        latex.append(r" \begin{itemize}[leftmargin=0.15in, label={}]")
        latex.append(r"    \small{\item{")
        
        if isinstance(skills, list):
            # If skills is a list of strings
            if all(isinstance(s, str) for s in skills):
                latex.append(f"     \\textbf{{Skills}}: {{ {', '.join(skills)} }} \\\\")
            else:
                # Handle potential object structure
                for s in skills:
                    if isinstance(s, dict):
                        cat = s.get('category', 'Skills')
                        items = s.get('items', [])
                        if isinstance(items, list):
                            latex.append(f"     \\textbf{{{cat}}}: {{ {', '.join(items)} }} \\\\")
                    elif isinstance(s, str):
                        latex.append(f"     {s} \\\\")
        
        latex.append(r"    }}")
        latex.append(r" \end{itemize}")
        latex.append("")

    # Experience
    if experience:
        latex.append(r"\section{Experience}")
        latex.append(r"  \resumeSubHeadingListStart")
        for exp in experience:
            comp = exp.get('company', 'Company')
            role = exp.get('role', 'Role')
            dur = exp.get('duration', 'Duration')
            desc = exp.get('description', '')
            
            latex.append(f"    \\resumeSubheading{{{comp}}}{{{dur}}}{{{role}}}{{}}")
            latex.append(r"      \resumeItemListStart")
            if isinstance(desc, str):
                for bullet in desc.split('\n'):
                    if bullet.strip():
                        # Basic escape for LaTeX special characters
                        b = bullet.strip().lstrip('-').lstrip('•').strip()
                        b = b.replace('&', r'\&').replace('%', r'\%').replace('$', r'\$')
                        latex.append(f"        \\resumeItem{{{b}}}")
            elif isinstance(desc, list):
                for b in desc:
                    b = str(b).replace('&', r'\&').replace('%', r'\%').replace('$', r'\$')
                    latex.append(f"        \\resumeItem{{{b}}}")
            latex.append(r"      \resumeItemListEnd")
        latex.append(r"  \resumeSubHeadingListEnd")
        latex.append("")

    # Projects
    if projects:
        latex.append(r"\section{Projects}")
        latex.append(r"  \resumeSubHeadingListStart")
        for proj in projects:
            title = proj.get('title', 'Project Title')
            tech = proj.get('technologies', [])
            if isinstance(tech, list): tech = ", ".join(tech)
            link = proj.get('link', '')
            desc = proj.get('description', '')
            
            header = f"\\textbf{{{title}}}"
            if tech: header += f" $|$ \\emph{{{tech}}}"
            latex.append(f"    \\resumeProjectHeading{{{header}}}{{{link}}}")
            latex.append(r"      \resumeItemListStart")
            if isinstance(desc, str):
                for bullet in desc.split('\n'):
                    if bullet.strip():
                        b = bullet.strip().lstrip('-').lstrip('•').strip()
                        b = b.replace('&', r'\&').replace('%', r'\%').replace('$', r'\$')
                        latex.append(f"        \\resumeItem{{{b}}}")
            elif isinstance(desc, list):
                for b in desc:
                    b = str(b).replace('&', r'\&').replace('%', r'\%').replace('$', r'\$')
                    latex.append(f"        \\resumeItem{{{b}}}")
            latex.append(r"      \resumeItemListEnd")
        latex.append(r"  \resumeSubHeadingListEnd")
        latex.append("")

    # Achievements
    if achievements:
        latex.append(r"\section{Achievements}")
        latex.append(r"  \resumeItemListStart")
        for ach in achievements:
            ach = str(ach).replace('&', r'\&').replace('%', r'\%').replace('$', r'\$')
            latex.append(f"    \\resumeItem{{{ach}}}")
        latex.append(r"  \resumeItemListEnd")
        latex.append("")

    latex.append(r"\end{document}")
    
    return "\n".join(latex)
