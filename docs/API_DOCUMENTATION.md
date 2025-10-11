# Enhanced HealthFlow AI Digital Prescription System - API Documentation

## 1. Introduction

This document provides a comprehensive overview of the Enhanced HealthFlow API, a RESTful interface for interacting with the AI Digital Prescription System. The API is designed to be secure, scalable, and easy to use, following the principles of the OpenAPI Specification (OAS) 3.0.

### 1.1. Base URL

The base URL for the production API is:

```
https://api.healthflow.egypt.gov/api/v1
```

### 1.2. Authentication

All API requests must be authenticated using a JSON Web Token (JWT) in the `Authorization` header:

```
Authorization: Bearer <your-jwt-token>
```

Tokens can be obtained by authenticating with the `/auth/login` endpoint.

### 1.3. Rate Limiting

The API is rate-limited to prevent abuse. The default rate limit is 100 requests per minute. Exceeding the rate limit will result in a `429 Too Many Requests` error.

## 2. Endpoints

### 2.1. Authentication

#### `POST /auth/login`

Authenticates a user and returns a JWT.

- **Request Body**:
    - `username` (string, required): The user's username.
    - `password` (string, required): The user's password.

- **Response**:
    - `access_token` (string): The JWT access token.
    - `refresh_token` (string): The JWT refresh token.

#### `POST /auth/register`

Registers a new user.

- **Request Body**:
    - `username` (string, required): The user's username.
    - `email` (string, required): The user's email address.
    - `password` (string, required): The user's password.
    - `first_name` (string, required): The user's first name.
    - `last_name` (string, required): The user's last name.

- **Response**:
    - `message` (string): A success message.

### 2.2. Prescriptions

#### `POST /prescriptions/upload`

Uploads a prescription for processing.

- **Request Body**:
    - `file` (file, required): The prescription file (PDF, PNG, JPG, etc.).

- **Response**:
    - `prescription_id` (string): The ID of the newly created prescription.

#### `GET /prescriptions`

Returns a list of prescriptions for the authenticated user.

- **Query Parameters**:
    - `page` (integer, optional): The page number to retrieve.
    - `per_page` (integer, optional): The number of items per page.

- **Response**:
    - `prescriptions` (array): A list of prescription objects.

#### `GET /prescriptions/{id}`

Returns the details of a specific prescription.

- **Path Parameters**:
    - `id` (string, required): The ID of the prescription.

- **Response**:
    - A prescription object.

### 2.3. FHIR

The Enhanced HealthFlow system exposes a FHIR R4 compliant API for interoperability. The FHIR API is available at the following base URL:

```
https://fhir.healthflow.egypt.gov/fhir/r4
```

For more information on the FHIR API, please refer to the official HL7 FHIR R4 documentation.

## 3. Error Handling

The API uses standard HTTP status codes to indicate the success or failure of a request.

- `200 OK`: The request was successful.
- `201 Created`: The resource was successfully created.
- `400 Bad Request`: The request was invalid.
- `401 Unauthorized`: Authentication is required.
- `403 Forbidden`: You do not have permission to access this resource.
- `404 Not Found`: The requested resource was not found.
- `429 Too Many Requests`: You have exceeded the rate limit.
- `500 Internal Server Error`: An unexpected error occurred.

Error responses will include a JSON body with the following format:

```json
{
  "error": "Error Type",
  "message": "A description of the error.",
  "status_code": 400
}
```


## 4. Versioning

The API is versioned using a URL prefix (`/api/v1`). When breaking changes are introduced, a new version will be released with a new prefix (e.g., `/api/v2`).

## 5. SDKs

To facilitate integration with the Enhanced HealthFlow API, we provide official SDKs for the following languages:

- **Python**: `pip install healthflow-sdk`
- **JavaScript/TypeScript**: `npm install @healthflow/sdk`

These SDKs provide a convenient way to interact with the API without having to handle the low-level details of HTTP requests and authentication.

