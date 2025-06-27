# This file has been commented out as the Payment model and related functionality have been removed.
# If needed in the future, uncomment and update the code to reference the appropriate model (e.g., SecurityDeposit).

# from django import forms
# from .models import Payment

# class PaymentForm(forms.ModelForm):
#     class Meta:
#         model = Payment
#         fields = ['amount', 'payment_method', 'payment_type', 'transaction_id', 'notes']
#         widgets = {
#             'amount': forms.NumberInput(attrs={
#                 'class': 'form-control',
#                 'step': '0.01',
#                 'min': '0',
#                 'required': True
#             }),
#             'payment_method': forms.Select(attrs={
#                 'class': 'form-select',
#                 'required': True
#             }),
#             'payment_type': forms.Select(attrs={
#                 'class': 'form-select',
#                 'required': True
#             }),
#             'transaction_id': forms.TextInput(attrs={
#                 'class': 'form-control',
#                 'placeholder': 'Leave blank for cash payments'
#             }),
#             'notes': forms.Textarea(attrs={
#                 'class': 'form-control',
#                 'rows': 2,
#                 'placeholder': 'Any additional notes about this payment'
#             })
#         }
#     
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         # Set required to False for transaction_id since it's optional for cash payments
#         self.fields['transaction_id'].required = False
