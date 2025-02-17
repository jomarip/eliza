module LoreSubmission {
    struct LoreProposal has key {
        content: String,
        submitter: address,
        votes: u64,
        status: u8,
        validation_hash: String
    }
    
    public entry fun submit_proposal(
        content: String,
        validation_hash: String
    ) acquires LoreProposal {
        // Matches validation system in src/models/lore_validator.py
        let account = &signer::address_of(signer);
        move_to(account, LoreProposal {
            content,
            submitter: *account,
            votes: 0,
            status: 0,
            validation_hash
        });
    }
} 