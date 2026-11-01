from django import forms

class RepositoryUploadForm(forms.Form):
    repository_name = forms.CharField(
        max_length=180,
        label="Project name",
        widget=forms.TextInput(attrs={
            "placeholder": "e.g. ecommerce-backend, my-api-service",
            "class": "field input-text",
            "autocomplete": "off",
            "required": "required",
        })
    )
    repository_zip = forms.FileField(
        label="Repository ZIP",
        widget=forms.FileInput(attrs={
            "class": "file-input",
            "accept": ".zip,application/zip,application/x-zip-compressed",
            "id": "zip-upload-input",
            "required": "required",
        })
    )

    def clean_repository_zip(self):
        file = self.cleaned_data.get("repository_zip")
        if not file:
            raise forms.ValidationError("Please select a ZIP file to upload.")
        if not file.name.lower().endswith(".zip"):
            raise forms.ValidationError("Please upload a file ending with .zip extension.")
        if file.size > 15 * 1024 * 1024:
            raise forms.ValidationError("For this MVP, ZIP archives must be 15 MB or smaller.")
        return file
