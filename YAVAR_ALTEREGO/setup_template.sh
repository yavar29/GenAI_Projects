#!/bin/bash

# AI Alter Ego Template Setup Script
# This script helps create a clean template version of the project

echo "🤖 Setting up AI Alter Ego Template..."

# Create backup of original files
echo "📦 Creating backup of original files..."
mkdir -p backup/original_kb
mkdir -p backup/original_me
cp -r kb/* backup/original_kb/ 2>/dev/null || true
cp -r me/* backup/original_me/ 2>/dev/null || true

# Clean personal data from me folder
echo "🧹 Cleaning personal data from me/ folder..."
rm -f me/linkedin.pdf
rm -f me/summary.txt

# Create template files
echo "📝 Creating template files..."

# Create template README for knowledge base
cat > kb/README.md << 'EOF'
# Knowledge Base Template

This directory contains template files for your AI Alter Ego knowledge base.

## Structure

- `faq/` - Frequently Asked Questions templates
- `projects/` - Project documentation templates  
- `resume/` - Resume and professional data templates
- `portfolio/` - Portfolio materials templates

## Setup Instructions

1. **Replace Template Content**: All files ending with `-template.md` or `-template.txt` should be customized with your own information
2. **Remove Template Suffix**: After customizing, rename files to remove the `-template` suffix
3. **Add Your Data**: Replace placeholder content with your actual information
4. **Organize Structure**: Maintain the folder structure but customize the content

## File Naming Convention

- `*-template.md` - Template files to be customized
- `*-example.md` - Example files showing the format
- Regular files - Your actual content (after customization)

## Privacy Note

Make sure to review all content before making it public. Remove any sensitive personal information.
EOF

# Create template for contact information
cat > kb/faq/contact-information-template.md << 'EOF'
---
title: Contact Information Template
updated: 2025-01-15
tags: [contact, template]
---

## Professional Contact Information

**Email**: [your.email@example.com]
**Phone**: [your phone number]
**LinkedIn**: [your LinkedIn profile URL]
**GitHub**: [your GitHub profile URL]
**Portfolio Website**: [your portfolio URL]

## Location & Availability

**Current Location**: [your city, country]
**Available for**: [remote work, relocation, etc.]
**Start Date**: [when you're available to start]

## Preferred Contact Methods

- **Primary**: Email
- **Secondary**: LinkedIn
- **Response Time**: [e.g., within 24 hours]

---

**Note**: Replace all placeholder information with your actual contact details.
EOF

echo "✅ Template setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Customize all template files with your information"
echo "2. Remove '-template' suffix from customized files"
echo "3. Review content for any sensitive information"
echo "4. Test the application with your customized content"
echo ""
echo "🔒 Original files backed up in backup/ directory"
