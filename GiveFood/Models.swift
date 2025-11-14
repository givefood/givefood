struct DonationPointDetail: Codable {
    // Existing fields...

    var opening_hours: String?
    var wheelchair_accessible: Bool?
    var politics: PoliticsObject?

    enum CodingKeys: String, CodingKey {
        // Existing keys...
        
        case opening_hours
        case wheelchair_accessible
        case politics
    }
}

struct PoliticsObject: Codable {
    // Define the properties of the politics object as needed
}