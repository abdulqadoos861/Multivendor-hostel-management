from django import forms

class MonthlyFeePaymentForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0',
            'required': True
        })
    )
    payment_method = forms.ChoiceField(
        choices=[('Cash', 'Cash'), ('Bank Transfer', 'Bank Transfer'), ('Online Payment', 'Online Payment')],
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        })
    )
    payment_type = forms.ChoiceField(
        choices=[('Monthly Fee', 'Monthly Fee')],
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        })
    )
    transaction_id = forms.CharField(
        max_length=100, 
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Leave blank for cash payments'
        })
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Any additional notes about this payment'
        })
    )
