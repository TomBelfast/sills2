// Handle form submission for new sill
document.getElementById('sillForm')?.addEventListener('submit', function(e) {
    // Let the form submit normally - no need to prevent default
    return true;
});

// Function to format UK phone number for WhatsApp
function formatUKPhoneForWhatsApp(phone) {
    // Remove all spaces, hyphens, brackets and other special characters
    let cleanPhone = phone.replace(/[^0-9+]/g, '');
    
    // If the number starts with '0', replace it with '+44'
    if (cleanPhone.startsWith('0')) {
        cleanPhone = '44' + cleanPhone.substring(1);
    }
    
    // If the number doesn't start with '+' or '44', add '44' at the beginning
    if (!cleanPhone.startsWith('+') && !cleanPhone.startsWith('44')) {
        cleanPhone = '44' + cleanPhone;
    }
    
    // Ensure the number starts with '+'
    if (!cleanPhone.startsWith('+')) {
        cleanPhone = '+' + cleanPhone;
    }
    
    return cleanPhone;
}

// Function to delete a sill
function deleteSill(sillId) {
    if (confirm('Are you sure you want to delete this window sill?')) {
        fetch(`/sills/${sillId}`, {
            method: 'DELETE'
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
}

// Function to populate edit modal
function editSill(id, clientId, length, depth, color, sillType, location, has95mm) {
    document.getElementById('edit_sill_id').value = id;
    document.getElementById('edit_client').value = clientId;
    document.getElementById('edit_length').value = length;
    document.getElementById('edit_depth').value = depth;
    document.getElementById('edit_color').value = color;
    document.getElementById('edit_sill_type').value = sillType;
    document.getElementById('edit_location').value = location;
    document.getElementById('edit_has_95mm').checked = has95mm;
    
    const editModal = new bootstrap.Modal(document.getElementById('editModal'));
    editModal.show();
}

// Function to update sill
function updateSill() {
    const formData = new FormData(document.getElementById('editForm'));
    const sillId = document.getElementById('edit_sill_id').value;
    
    fetch(`/sills/${sillId}`, {
        method: 'PUT',
        body: formData
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
        alert('An error occurred while updating the sill');
    });
}
