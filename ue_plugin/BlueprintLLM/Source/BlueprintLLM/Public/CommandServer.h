#pragma once

#include "CoreMinimal.h"
#include "Common/TcpListener.h"
#include "Sockets.h"

DECLARE_LOG_CATEGORY_EXTERN(LogBlueprintLLM, Log, All);

struct FCommandResult
{
	bool bSuccess = false;
	TSharedPtr<FJsonObject> Data;
	FString ErrorMessage;

	static FCommandResult Ok(TSharedPtr<FJsonObject> InData = nullptr)
	{
		FCommandResult R;
		R.bSuccess = true;
		R.Data = InData;
		return R;
	}

	static FCommandResult Error(const FString& Message)
	{
		FCommandResult R;
		R.bSuccess = false;
		R.ErrorMessage = Message;
		return R;
	}
};

/**
 * TCP command server for BlueprintLLM.
 * Listens on localhost:13377 for JSON commands.
 * Dispatches to handlers on the game thread.
 */
class FCommandServer
{
public:
	FCommandServer();
	~FCommandServer();

	/** Start listening. Returns true if the listener bound successfully. */
	bool Start(int32 Port = 13377);

	/** Stop the server and close all connections. */
	void Stop();

	/** Is the server currently listening? */
	bool IsRunning() const { return bRunning; }

private:
	// Connection handling
	bool OnConnectionAccepted(FSocket* ClientSocket, const FIPv4Endpoint& ClientEndpoint);
	void ProcessClient(FSocket* ClientSocket);
	FString ReadLine(FSocket* Socket);
	void SendResponse(FSocket* Socket, const FCommandResult& Result);

	// Command dispatch
	FCommandResult DispatchCommand(const FString& Command, const TSharedPtr<FJsonObject>& Params);

	// Command handlers
	FCommandResult HandleHealthCheck(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleImportFromIR(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleGetBlueprintInfo(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleCompileBlueprint(const TSharedPtr<FJsonObject>& Params);
	FCommandResult HandleDeleteBlueprint(const TSharedPtr<FJsonObject>& Params);

	// Helpers
	UBlueprint* FindBlueprintByName(const FString& Name);
	bool DeleteExistingBlueprint(const FString& Name);

	FTcpListener* Listener = nullptr;
	bool bRunning = false;
	TArray<FSocket*> ActiveClients;
	FCriticalSection ClientsMutex;

	static constexpr int32 DEFAULT_PORT = 13377;
	static const FString SERVER_VERSION;
};
