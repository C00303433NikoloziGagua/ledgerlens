from pathlib import Path

from django import forms

from .uploads import ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE, detect_file_type


class UploadForm(forms.Form):
    file = forms.FileField(
        label='Invoice (PDF, PNG or JPG, up to 10 MB)',
        widget=forms.FileInput(attrs={'accept': '.pdf,.png,.jpg,.jpeg'}),
    )

    # size, extension and real contents
    def clean_file(self):
        uploaded = self.cleaned_data['file']

        if uploaded.size > MAX_UPLOAD_SIZE:
            raise forms.ValidationError('The file is bigger than 10 MB.')

        extension = Path(uploaded.name).suffix.lower()
        expected_type = ALLOWED_EXTENSIONS.get(extension)

        if expected_type is None:
            raise forms.ValidationError('Only PDF, PNG and JPG files are allowed.')

        if detect_file_type(uploaded) != expected_type:
            raise forms.ValidationError("The file's contents don't match its type.")

        return uploaded
