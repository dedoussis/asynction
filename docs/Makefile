# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS                 ?=
SPHINXBUILD   			   ?= sphinx-build
SOURCEDIR     			   = .
BUILDDIR      			   = _build
S3_BUCKET_NAME 			   = ${DOCS_WEBSITE_S3_BUCKET}
CLOUDFRONT_DISTRIBUTION_ID = ${DOCS_WEBSITE_S3_BUCKET}


# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

publish:
	./deploy.sh $(BUILDDIR)/html $(S3_BUCKET_NAME) $(CLOUDFRONT_DISTRIBUTION_ID)

.PHONY: help publish Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
