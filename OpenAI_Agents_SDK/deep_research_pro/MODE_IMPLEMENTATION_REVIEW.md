# Mode Implementation Review & Recommendations

## ✅ Completed Changes

### 1. **WriterAgent Instructions** (`app/agents/writer_agent.py`)
- ✅ **Status**: Complete
- **Implementation**: Single unified instruction set covering all three modes (General, Debate, Timeline)
- **Structure**: 
  - Shared rules for all modes (citations, synthesis, evidence grounding)
  - Mode-specific sections with clear guidance
  - Output requirements clearly defined
- **Strengths**: 
  - Single source of truth
  - Clear separation of mode-specific behavior
  - Comprehensive guidance for each mode

### 2. **Prompt Building** (`app/agents/writer_agent.py`)
- ✅ **Status**: Complete
- **Implementation**: `_build_prompt` function injects mode and side labels
- **Features**:
  - Explicit `MODE: {mode}` declaration
  - Side labels for Debate mode (SIDE_A, SIDE_B)
  - Mode-specific instruction reminders
- **Strengths**: Clean, explicit mode context injection

### 3. **ResearchManager Mode Support** (`app/core/research_manager.py`)
- ✅ **Status**: Complete
- **Implementation**: 
  - `__init__` accepts `mode` and `side_labels` parameters
  - Mode-based branching in synthesis step
  - Separate methods: `_write_report`, `_write_debate_report`, `_write_timeline_report`
- **Features**:
  - Mode-aware status messages
  - Proper yield format for UI consumption
  - Side labels passed through to WriterAgent
- **Strengths**: Clean separation of concerns, proper async handling

### 4. **Gradio UI** (`app/ui/gradio_app.py`)
- ✅ **Status**: Complete
- **Implementation**:
  - Mode dropdown with three options
  - Conditional Side A/B label inputs (visible only in Debate mode)
  - Mode-based output display (debate transcript + judge summary vs. standard report)
  - Dynamic visibility control
- **Features**:
  - `toggle_debate_labels()` function shows/hides side label inputs
  - All button handlers pass mode and side labels
  - Export functions handle mode-specific content
- **Strengths**: Clean UX, proper state management

## 🔍 Current Implementation Analysis

### **Data Flow**
```
User selects mode → UI passes to run_research_stream → ResearchManager.__init__ 
→ Mode stored in self.mode → Synthesis step branches on mode 
→ Calls appropriate _write_*_report method → WriterAgent receives mode + side_labels 
→ _build_prompt injects mode context → LLM generates mode-appropriate output
```

### **Mode-Specific Behavior**

#### **General Mode**
- ✅ Adaptive structure (5-10 sections)
- ✅ Query-type inference
- ✅ Key insights, practical implications, limitations
- ✅ Standard report display

#### **Debate Mode**
- ✅ Structured debate transcript (Speaker A/B turns)
- ✅ Judge Summary section
- ✅ Custom side labels support
- ✅ Two-column UI layout (debate + judge)
- ✅ Side labels passed through entire pipeline

#### **Timeline Mode**
- ✅ Chronological organization
- ✅ Timeline overview, era-based sections
- ✅ Recent developments, future outlook
- ✅ Standard report display

## 🎯 Recommendations for Refinement

### **1. Citation Post-Processing (Medium Priority)**
**Current State**: `_write_debate_report` and `_write_timeline_report` don't post-process citations like `_write_report` does.

**Issue**: Citations in debate/timeline reports may not be properly extracted and validated.

**Recommendation**: 
```python
# In _write_debate_report and _write_timeline_report, add citation post-processing:
from app.schemas.report import Section
import re

processed_sections: List[Section] = []
for sec in report.sections:
    citation_ids = set()
    pattern = r'\[(\d+)\]'
    matches = re.findall(pattern, sec.summary)
    for match in matches:
        try:
            citation_id = int(match)
            if citation_id in id_to_source:
                citation_ids.add(citation_id)
        except ValueError:
            continue
    
    processed_sections.append(Section(
        title=sec.title,
        summary=sec.summary,
        citations=sorted(citation_ids),
    ))
report.sections = processed_sections
```

### **2. Side Label Parsing from Query (Low Priority)**
**Current State**: Side labels default to "Side A" / "Side B" or user-provided values.

**Enhancement**: Automatically extract side labels from debate queries like "China vs USA" or "Pro vs Con".

**Recommendation**:
```python
def _parse_side_labels_from_query(query: str) -> Optional[List[str]]:
    """Try to extract side labels from query text."""
    # Patterns: "X vs Y", "X versus Y", "X or Y debate"
    patterns = [
        r'(.+?)\s+vs\.?\s+(.+)',
        r'(.+?)\s+versus\s+(.+)',
        r'(.+?)\s+or\s+(.+?)\s+debate',
    ]
    for pattern in patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            return [match.group(1).strip(), match.group(2).strip()]
    return None
```

### **3. Mode-Specific Query Generation (Medium Priority)**
**Current State**: QueryGeneratorAgent generates queries the same way for all modes.

**Enhancement**: Tailor query generation based on mode:
- **Debate**: Generate queries that explore both sides
- **Timeline**: Generate queries focused on historical events, dates, evolution
- **General**: Current behavior (balanced exploration)

**Recommendation**: Add mode parameter to `QueryGeneratorAgent.generate_async()` and adjust instructions.

### **4. Timeline Mode Date Extraction (Low Priority)**
**Current State**: Timeline mode relies on LLM to organize chronologically.

**Enhancement**: Extract dates from sources and use them to guide timeline organization.

**Recommendation**: 
- Parse `published` dates from sources
- Sort sources chronologically before passing to Writer
- Add date context to timeline prompt

### **5. Debate Mode Source Balancing (Medium Priority)**
**Current State**: All sources are passed to debate writer without consideration of which side they support.

**Enhancement**: Attempt to balance sources between sides or at least inform the writer about source distribution.

**Recommendation**:
```python
# In _write_debate_report, analyze source distribution:
side_a_sources = []  # Sources that might support Side A
side_b_sources = []  # Sources that might support Side B
neutral_sources = []  # Neutral or unclear

# Pass this context to the writer prompt
```

### **6. Error Handling for Mode-Specific Failures (Low Priority)**
**Current State**: Generic error handling.

**Enhancement**: Mode-specific error messages and fallback behavior.

**Recommendation**: Catch mode-specific errors (e.g., if debate fails to split judge summary) and provide helpful messages.

### **7. Mode Validation (Low Priority)**
**Current State**: Mode is passed as string without validation.

**Enhancement**: Validate mode at entry points.

**Recommendation**:
```python
VALID_MODES = ["General", "Debate", "Timeline"]

def validate_mode(mode: str) -> str:
    if mode not in VALID_MODES:
        return "General"  # Default fallback
    return mode
```

### **8. UI Polish (Low Priority)**
**Current State**: Basic mode dropdown and conditional inputs.

**Enhancements**:
- Add mode descriptions/tooltips
- Show mode-specific examples
- Add mode-specific help text
- Visual indicators for active mode

## 📊 Overall Assessment

### **Strengths**
1. ✅ **Clean Architecture**: Mode logic is well-separated and maintainable
2. ✅ **Single Source of Truth**: Writer instructions are unified and comprehensive
3. ✅ **Proper Data Flow**: Mode and side labels flow correctly through the pipeline
4. ✅ **Good UX**: Conditional UI elements, clear mode selection
5. ✅ **Extensible**: Easy to add new modes in the future

### **Areas for Improvement**
1. ⚠️ **Citation Post-Processing**: Missing in debate/timeline modes
2. ⚠️ **Mode-Aware Query Generation**: Could improve relevance
3. ⚠️ **Source Balancing**: Debate mode could benefit from balanced source distribution
4. ⚠️ **Error Handling**: Could be more mode-specific

### **Priority Recommendations**
1. **High**: Add citation post-processing to debate/timeline modes
2. **Medium**: Implement mode-aware query generation
3. **Medium**: Add source balancing for debate mode
4. **Low**: All other enhancements

## ✅ Conclusion

The mode implementation is **solid and functional**. The core architecture is clean, the data flow is correct, and the UI properly supports all three modes. The main gaps are:

1. Citation post-processing consistency across modes
2. Mode-aware query generation for better results
3. Source balancing for debate mode

These are refinements rather than critical issues. The current implementation should work well for generating mode-appropriate reports.

