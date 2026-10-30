from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render

from extraction.pipeline import run_pipeline
from extraction.schema import field_rows

from .forms import UploadForm
from .models import Document
from .uploads import CONTENT_TYPES, detect_file_type, file_sha256


# list of the user's own documents
@login_required
def home(request):
    return render(
        request,
        'documents/home.html',
        {'documents': request.user.documents.all()},
    )


# save the file, then run the pipeline straight away
@login_required
def upload(request):
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)

        if form.is_valid():
            uploaded = form.cleaned_data['file']

            document = Document.objects.create(
                owner=request.user,
                file=uploaded,
                original_name=uploaded.name,
                file_type=detect_file_type(uploaded),
                size=uploaded.size,
                sha256=file_sha256(uploaded),
            )

            run_pipeline(document)
            return redirect('document_detail', pk=document.pk)
    else:
        form = UploadForm()

    return render(request, 'documents/upload.html', {'form': form})


# one document, 404 unless it belongs to the user
@login_required
def detail(request, pk):
    document = get_object_or_404(Document, pk=pk, owner=request.user)
    extraction = document.extractions.first()

    rows = []
    if extraction and extraction.fields:
        rows = field_rows(document.document_type, extraction.fields)

    return render(
        request,
        'documents/detail.html',
        {'document': document, 'extraction': extraction, 'rows': rows},
    )


# the original file, owner only
@login_required
def original_file(request, pk):
    document = get_object_or_404(Document, pk=pk, owner=request.user)

    return FileResponse(
        document.file.open('rb'),
        content_type=CONTENT_TYPES[document.file_type],
        filename=document.original_name,
    )
