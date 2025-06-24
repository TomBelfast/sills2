document.addEventListener('DOMContentLoaded', function() {
    // Restore last selected values
    const colorSelect = document.getElementById('color');
    const clientSelect = document.getElementById('client_id');
    const clientSelectDropdown = document.getElementById('client_select');
    
    // Restore color selection
    const lastColor = localStorage.getItem('lastSelectedColor');
    if (lastColor && colorSelect) {
        colorSelect.value = lastColor;
    }

    // Restore client selection
    const lastClient = localStorage.getItem('lastSelectedClient');
    if (lastClient && clientSelect) {
        clientSelect.value = lastClient;
    }

    // Save selections when they change
    if (colorSelect) {
        colorSelect.addEventListener('change', function() {
            localStorage.setItem('lastSelectedColor', this.value);
        });
    }

    if (clientSelect) {
        clientSelect.addEventListener('change', function() {
            localStorage.setItem('lastSelectedClient', this.value);
        });
    }

    // Handle form submission for new sill
    const sillForm = document.getElementById('sillForm');
    let isSubmitting = false;
    
    if (sillForm) {
        sillForm.addEventListener('submit', function(e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            
            if (isSubmitting) {
                return false;
            }
            
            isSubmitting = true;
            const submitButton = this.querySelector('button[type="submit"]');
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.textContent = 'Adding...';
            }
            
            const formData = new FormData(this);
            
            fetch('/sills', {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    window.location.reload();
                } else {
                    alert('Error: ' + (data.message || 'Unknown error occurred'));
                    isSubmitting = false;
                    if (submitButton) {
                        submitButton.disabled = false;
                        submitButton.textContent = 'Add Window Sill';
                    }
                }
            })
            .catch(error => {
                isSubmitting = false;
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.textContent = 'Add Window Sill';
                }
                handleFetchError(error, 'adding the sill');
            });
        });
    }

    // Handle settings form submission
    const settingsForm = document.getElementById('settingsForm');
    if (settingsForm) {
        settingsForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            
            fetch('/update_settings', {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    alert('Settings updated successfully!');
                    window.location.reload();
                } else {
                    alert('Error: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while updating settings');
            });
        });
    }

    // Delete sill function
    window.deleteSill = function(id) {
        if (confirm('Are you sure you want to delete this window sill?')) {
            fetch(`/sills/${id}`, {
                method: 'DELETE',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    window.location.reload();
                } else {
                    alert('Error: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while deleting the sill');
            });
        }
    };

    // Edit sill function
    window.editSill = function(id, clientId, length, depth, color, sillType, location, has95mm) {
        try {
            // Ustawianie wartości w formularzu
            const fields = {
                'edit_sill_id': { value: id },
                'edit_client': { value: clientId },
                'edit_length': { value: length },
                'edit_depth': { value: depth },
                'edit_color': { value: color },
                'edit_sill_type': { value: sillType },
                'edit_location': { value: location },
                'edit_has_95mm': { checked: has95mm }
            };

            // Ustawianie wartości dla każdego pola
            Object.entries(fields).forEach(([elementId, props]) => {
                const element = document.getElementById(elementId);
                if (element) {
                    Object.entries(props).forEach(([prop, value]) => {
                        element[prop] = value;
                    });
                }
            });

            // Pokazanie modalu
            const editModal = new bootstrap.Modal(document.getElementById('editModal'));
            editModal.show();
        } catch (error) {
            console.error('Error in editSill:', error);
            alert('Error preparing edit form: ' + error.message);
        }
    };

    // Save changes function
    window.saveSillChanges = function() {
        const form = document.getElementById('editForm');
        const formData = new FormData(form);
        const sillId = document.getElementById('edit_sill_id').value;

        fetch(`/sills/${sillId}`, {
            method: 'PUT',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                const editModal = bootstrap.Modal.getInstance(document.getElementById('editModal'));
                if (editModal) {
                    editModal.hide();
                }
                window.location.reload();
            } else {
                alert('Error: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while updating the sill');
        });
    };

    // Handle client selection
    if (clientSelectDropdown) {
        clientSelectDropdown.addEventListener('change', function() {
            const clientId = this.value;
            if (clientId) {
                window.location.href = `/set_active_client/${clientId}`;
            }
        });
    }
});

// Clear stored client when leaving the page
window.addEventListener('beforeunload', function() {
    // Optionally clear the client selection when leaving the page
    // Uncomment the next line if you want to clear client selection on page leave
    // localStorage.removeItem('lastSelectedClient');
});

function handleFetchError(error, action) {
    console.error(`Error during ${action}:`, error);
    alert(`An error occurred while ${action}. Please try again or contact support if the problem persists.`);
}
