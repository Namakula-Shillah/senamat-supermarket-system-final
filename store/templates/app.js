document.addEventListener("DOMContentLoaded", () => {
  const pageState = new URLSearchParams(location.search);
  if (pageState.has("deleted")) {
    const deleteNotice = document.querySelector(".notice-success");
    if (deleteNotice) {
      window.setTimeout(() => deleteNotice.remove(), 3000);
    }
  }

  // Only the model entry form opts into this client-side validation.
  const form = document.querySelector("form[data-validate]");
  const notices = document.querySelector(".notification-stack");

  const formModal = document.querySelector("[data-form-modal]");
  const openFormButton = document.querySelector("[data-open-form]");
  if (formModal && openFormButton) {
    document.body.append(formModal);
    let modalTrigger = openFormButton;
    const closeForm = () => {
      formModal.hidden = true;
      formModal.setAttribute("aria-hidden", "true");
      document.body.classList.remove("modal-open");
      const currentUrl = new URL(location.href);
      currentUrl.searchParams.delete("add");
      currentUrl.searchParams.delete("edit");
      history.replaceState(null, "", currentUrl);
      modalTrigger.focus();
    };

    openFormButton.addEventListener("click", () => {
      modalTrigger = openFormButton;
      formModal.hidden = false;
      formModal.setAttribute("aria-hidden", "false");
      document.body.classList.add("modal-open");
      formModal.querySelector("input:not([type='hidden']), select, textarea")?.focus();
    });

    formModal.querySelector("[data-close-form]")?.addEventListener("click", closeForm);
    formModal.addEventListener("click", event => {
      if (event.target === formModal) closeForm();
    });
    document.addEventListener("keydown", event => {
      if (event.key === "Escape" && !formModal.hidden) closeForm();
    });

    if (!formModal.hidden) {
      document.body.classList.add("modal-open");
      formModal.querySelector("input:not([type='hidden']), select, textarea")?.focus();
    }
  }

  // Add an accessible notice when browser validation blocks a submission.
  function showNotice(text) {
    if (!notices) return;
    const notice = document.createElement("div");
    notice.className = "notice notice-error";
    notice.setAttribute("role", "alert");
    notice.textContent = text;
    notices.appendChild(notice);
  }

  if (form) {
    // Clear a custom required-field error as soon as the user edits that field.
    form.addEventListener("input", event => {
      if (typeof event.target.setCustomValidity === "function") {
        event.target.setCustomValidity("");
      }
    });

    // Block invalid data in the browser; valid data continues to Django by POST.
    form.addEventListener("submit", event => {
      const emptyRequiredField = [...form.elements].find(field =>
        field.required && !field.value.trim()
      );

      if (emptyRequiredField) {
        emptyRequiredField.setCustomValidity("This field is required.");
      }

      if (!form.checkValidity()) {
        const invalidField = [...form.elements].find(field =>
          field.willValidate && !field.validity.valid
        );
        const label = invalidField && form.querySelector(`label[for="${invalidField.id}"]`);
        const fieldName = label ? label.textContent.trim() : "Form";
        event.preventDefault();
        form.reportValidity();
        showNotice(`${fieldName}: ${invalidField.validationMessage} The record was not saved.`);
      }
    });
  }

  const customerSelect = document.querySelector("#id_customer");
  const customerSpending = document.querySelector("#customer-spending");
  const customerSpendingData = document.querySelector("#customer-spending-data");
  if (customerSelect && customerSpending && customerSpendingData) {
    const spendingByCustomer = new Map(
      JSON.parse(customerSpendingData.textContent).map(item => [
        String(item.pk),
        Number(item.amount_spent),
      ])
    );
    const updateCustomerSpending = () => {
      const amount = spendingByCustomer.get(customerSelect.value) || 0;
      customerSpending.textContent = `Customer amount spent: ${amount.toFixed(2)} shs`;
    };
    customerSelect.addEventListener("change", updateCustomerSpending);
    updateCustomerSpending();
  }

  const receiptSheet = document.querySelector("[data-receipt-total]");
  const receiptPayment = document.querySelector("[data-receipt-payment]");
  const receiptBalance = document.querySelector("[data-receipt-balance]");
  const receiptPaid = document.querySelector("[data-receipt-paid]");
  const printReceiptButton = document.querySelector("[data-print-receipt]");
  if (receiptSheet && receiptPayment && receiptBalance && receiptPaid && printReceiptButton) {
    const total = Number(receiptSheet.dataset.receiptTotal);
    const savedAmount = Number(receiptSheet.dataset.savedAmount);
    const formatAmount = amount => `${amount.toFixed(2)} shs`;
    const updateReceiptBalance = () => {
      const amountPaid = Number(receiptPayment.value);
      const validAmount = Number.isFinite(amountPaid) && amountPaid >= total && total > 0;
      receiptBalance.textContent = validAmount
        ? formatAmount(amountPaid - total)
        : `Amount paid must cover ${formatAmount(total)}`;
      receiptPaid.textContent = amountPaid > 0 ? formatAmount(amountPaid) : "Not entered";
      printReceiptButton.disabled = !validAmount || amountPaid !== savedAmount;
    };
    receiptPayment.addEventListener("input", updateReceiptBalance);
    updateReceiptBalance();
  }

  // Confirm deletion because some model relationships cascade to child records.
  document.querySelectorAll("form[data-confirm-delete]").forEach(deleteForm => {
    let confirmed = false;
    deleteForm.addEventListener("submit", event => {
      if (confirmed) return;

      event.preventDefault();
      if (!notices) return;

      const previousConfirmation = notices.querySelector(".notice-confirmation");
      if (previousConfirmation) previousConfirmation.remove();

      const confirmation = document.createElement("section");
      confirmation.className = "notice notice-error notice-confirmation";
      confirmation.setAttribute("role", "alertdialog");
      confirmation.setAttribute("aria-labelledby", "delete-confirmation-title");

      const copy = document.createElement("div");
      copy.className = "notice-confirmation-copy";
      const title = document.createElement("strong");
      title.id = "delete-confirmation-title";
      title.textContent = "Confirm deletion";
      const detail = document.createElement("p");
      detail.textContent = "Are you sure you want to delete this record? Related records may also be deleted.";
      copy.append(title, detail);

      const actions = document.createElement("div");
      actions.className = "notice-confirmation-actions";
      const cancelButton = document.createElement("button");
      cancelButton.type = "button";
      cancelButton.className = "btn btn-secondary";
      cancelButton.textContent = "Cancel";
      cancelButton.addEventListener("click", () => {
        confirmation.remove();
        deleteForm.querySelector("button[type='submit']")?.focus();
      });

      const confirmButton = document.createElement("button");
      confirmButton.type = "button";
      confirmButton.className = "btn btn-danger";
      confirmButton.textContent = "Delete record";
      confirmButton.addEventListener("click", () => {
        confirmed = true;
        confirmation.remove();
        deleteForm.requestSubmit();
      });

      actions.append(cancelButton, confirmButton);
      confirmation.append(copy, actions);
      notices.prepend(confirmation);
      confirmButton.focus();
    });
  });
});