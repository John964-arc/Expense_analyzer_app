function toggleProfileSidebar() {
    const sidebar = document.getElementById('profileSidebar');
    const overlay = document.getElementById('profileSidebarOverlay');
    sidebar.classList.toggle('active');
    overlay.classList.toggle('active');
}

// Avatar Preview
document.getElementById('profile_picture')?.addEventListener('change', function(e) {
    if (e.target.files && e.target.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            let container = document.getElementById('avatarPreviewContainer');
            let img = document.getElementById('avatarPreviewImg');
            
            if(!img) {
                // Remove placeholder
                let placeholder = document.getElementById('avatarPlaceholder');
                if(placeholder) placeholder.remove();
                
                // Create image element
                img = document.createElement('img');
                img.id = 'avatarPreviewImg';
                // Insert before overlay
                container.insertBefore(img, container.querySelector('.avatar-overlay'));
            }
            img.src = e.target.result;
        }
        reader.readAsDataURL(e.target.files[0]);
    }
});

// Save Profile AJAX
function saveProfile() {
    const form = document.getElementById('profileForm');
    const formData = new FormData(form);
    
    const btn = document.getElementById('saveProfileBtn');
    const progress = document.getElementById('profileProgress');
    
    btn.disabled = true;
    btn.innerText = "Saving...";
    progress.style.display = "block";
    progress.style.color = "var(--text-secondary)";
    progress.innerText = "Uploading data...";
    
    fetch('/auth/profile/update', {
        method: 'POST',
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        btn.disabled = false;
        btn.innerText = "Save Changes";
        if(data.success) {
            progress.style.color = "var(--success)";
            progress.innerText = "Profile updated successfully!";
            
            // Update topbar UI
            const topbarUsrName = document.getElementById('topbarUsername');
            if(topbarUsrName) topbarUsrName.innerText = data.username;
            
            if(data.profile_picture) {
                const tvt = document.getElementById('topbarAvatarLetter');
                if(tvt) {
                    const img = document.createElement('img');
                    img.src = "/static/" + data.profile_picture;
                    img.className = "user-avatar";
                    img.style.objectFit = "cover";
                    img.id = "topbarAvatarImg";
                    tvt.parentNode.replaceChild(img, tvt);
                } else {
                    const img = document.getElementById('topbarAvatarImg');
                    if(img) img.src = "/static/" + data.profile_picture;
                }
            }
            
            setTimeout(() => toggleProfileSidebar(), 1500);
        } else {
            progress.style.color = "var(--danger)";
            progress.innerText = data.error || "An error occurred.";
        }
    })
    .catch(err => {
        btn.disabled = false;
        btn.innerText = "Save Changes";
        progress.style.color = "var(--danger)";
        progress.innerText = "Connection error.";
    });
}
